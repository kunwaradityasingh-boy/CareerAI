from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database import get_db
from backend.models import User, PendingRegistration, OTPChallenge
from backend.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from backend.core.config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    OTP_MAX_ATTEMPTS,
    OTP_MAX_REQUESTS_PER_HOUR,
    OTP_RESEND_COOLDOWN_SECONDS,
)
from backend.services.otp_service import (
    create_otp_challenge,
    verify_otp_challenge,
    hash_otp,
    verify_otp,
    OTPCooldownError,
    OTPLimitError,
    OTPExpiredError,
    OTPInvalidError,
)
from backend.services.registration_service import (
    start_registration,
    verify_registration,
    resend_registration_otp,
)


# ---------------------------------------------------------------------------
# Test Database Fixtures (In-Memory SQLite, 100% Isolated)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_engine():
    """Create an in-memory SQLite engine with StaticPool for cross-thread sharing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Only create auth-relevant tables
    User.__table__.create(engine)
    PendingRegistration.__table__.create(engine)
    OTPChallenge.__table__.create(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Provide a clean DB session for each test, truncating tables after."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        # Clean up tables
        session.query(OTPChallenge).delete()
        session.query(PendingRegistration).delete()
        session.query(User).delete()
        session.commit()
        session.close()


@pytest.fixture
def client(test_engine, db_session):
    """FastAPI TestClient wired to the isolated in-memory test database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. REGISTRATION TESTS
# ---------------------------------------------------------------------------

def test_valid_registration(client, db_session):
    """Submitting valid registration creates PendingRegistration and sends OTP."""
    with patch("backend.services.registration_service.send_email") as mock_email:
        mock_email.return_value = {"success": True, "message_id": "msg_123"}

        response = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Jane Doe",
                "email": "jane@example.com",
                "password": "Password123!",
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert data["email"] == "jane@example.com"
        assert "Verification code sent" in data["message"]

        # Verify PendingRegistration exists
        pending = db_session.scalar(
            select(PendingRegistration).where(
                PendingRegistration.email == "jane@example.com"
            )
        )
        assert pending is not None
        assert pending.name == "Jane Doe"
        assert verify_password("Password123!", pending.password_hash)

        # Permanent user must NOT exist
        permanent = db_session.scalar(
            select(User).where(User.email == "jane@example.com")
        )
        assert permanent is None

        # Verify OTP challenge created
        challenge = db_session.scalar(
            select(OTPChallenge).where(OTPChallenge.email == "jane@example.com")
        )
        assert challenge is not None
        assert challenge.purpose == "registration"
        assert challenge.consumed_at is None

        # Mock email was called
        mock_email.assert_called_once()


def test_duplicate_registered_email(client, db_session):
    """Registering with an already existing permanent email returns 409 Conflict."""
    existing_user = User(
        name="Existing User",
        email="existing@example.com",
        password_hash=hash_password("Password123!"),
    )
    db_session.add(existing_user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Another User",
            "email": "existing@example.com",
            "password": "NewPassword123!",
        },
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


def test_existing_active_pending_registration(client, db_session):
    """Submitting registration when active pending registration exists returns 409 Conflict."""
    now = datetime.now(timezone.utc)
    pending = PendingRegistration(
        name="Pending User",
        email="pending@example.com",
        password_hash=hash_password("Password123!"),
        expires_at=now + timedelta(minutes=10),
    )
    db_session.add(pending)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Pending User",
            "email": "pending@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 409
    assert "already pending" in response.json()["detail"].lower()


def test_expired_pending_registration_replaces_old(client, db_session):
    """Expired pending registration is safely replaced by new registration."""
    now = datetime.now(timezone.utc)
    old_pending = PendingRegistration(
        name="Old Name",
        email="expired@example.com",
        password_hash=hash_password("OldPassword123!"),
        expires_at=now - timedelta(minutes=1),
    )
    db_session.add(old_pending)
    db_session.commit()

    with patch("backend.services.registration_service.send_email") as mock_email:
        mock_email.return_value = {"success": True, "message_id": "msg_456"}

        response = client.post(
            "/api/v1/auth/register",
            json={
                "name": "New Name",
                "email": "expired@example.com",
                "password": "NewPassword123!",
            },
        )

        assert response.status_code == 202

        pending = db_session.scalar(
            select(PendingRegistration).where(
                PendingRegistration.email == "expired@example.com"
            )
        )
        assert pending.name == "New Name"
        assert verify_password("NewPassword123!", pending.password_hash)


def test_invalid_registration_data(client):
    """Invalid input fails schema validation with 422."""
    # Name too short
    res1 = client.post(
        "/api/v1/auth/register",
        json={"name": "A", "email": "valid@example.com", "password": "Password123!"},
    )
    assert res1.status_code == 422

    # Password too short (< 8)
    res2 = client.post(
        "/api/v1/auth/register",
        json={"name": "Valid Name", "email": "valid@example.com", "password": "short"},
    )
    assert res2.status_code == 422

    # Malformed email
    res3 = client.post(
        "/api/v1/auth/register",
        json={"name": "Valid Name", "email": "not-an-email", "password": "Password123!"},
    )
    assert res3.status_code == 422


# ---------------------------------------------------------------------------
# 2. OTP VERIFICATION & CONSUMPTION TESTS
# ---------------------------------------------------------------------------

def test_correct_otp_verification(client, db_session):
    """Successful OTP verification creates permanent User and cleans up PendingRegistration."""
    now = datetime.now(timezone.utc)
    pending = PendingRegistration(
        name="Alice Walker",
        email="alice@example.com",
        password_hash=hash_password("Secret123!"),
        expires_at=now + timedelta(minutes=15),
    )
    raw_otp = "123456"
    challenge = OTPChallenge(
        email="alice@example.com",
        purpose="registration",
        otp_hash=hash_otp(raw_otp),
        expires_at=now + timedelta(minutes=5),
        attempts=0,
    )
    db_session.add(pending)
    db_session.add(challenge)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/register/verify",
        json={"email": "alice@example.com", "otp": raw_otp},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice Walker"
    assert data["email"] == "alice@example.com"
    assert "id" in data

    # Permanent user was created
    user = db_session.scalar(select(User).where(User.email == "alice@example.com"))
    assert user is not None
    assert user.name == "Alice Walker"

    # Pending registration was deleted
    pending_check = db_session.scalar(
        select(PendingRegistration).where(PendingRegistration.email == "alice@example.com")
    )
    assert pending_check is None

    # OTP challenge was consumed
    challenge_check = db_session.scalar(
        select(OTPChallenge).where(OTPChallenge.email == "alice@example.com")
    )
    assert challenge_check.consumed_at is not None


def test_incorrect_otp_rejection(client, db_session):
    """Submitting incorrect OTP increments attempts and returns 400."""
    now = datetime.now(timezone.utc)
    pending = PendingRegistration(
        name="Bob",
        email="bob@example.com",
        password_hash=hash_password("Secret123!"),
        expires_at=now + timedelta(minutes=15),
    )
    challenge = OTPChallenge(
        email="bob@example.com",
        purpose="registration",
        otp_hash=hash_otp("111111"),
        expires_at=now + timedelta(minutes=5),
        attempts=0,
    )
    db_session.add(pending)
    db_session.add(challenge)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/register/verify",
        json={"email": "bob@example.com", "otp": "999999"},
    )

    assert response.status_code == 400
    assert "incorrect" in response.json()["detail"].lower()

    # Attempts incremented
    db_session.refresh(challenge)
    assert challenge.attempts == 1
    assert challenge.consumed_at is None


def test_expired_otp_rejection(client, db_session):
    """Submitting expired OTP returns 400 and consumes the OTP."""
    now = datetime.now(timezone.utc)
    pending = PendingRegistration(
        name="Charlie",
        email="charlie@example.com",
        password_hash=hash_password("Secret123!"),
        expires_at=now + timedelta(minutes=15),
    )
    challenge = OTPChallenge(
        email="charlie@example.com",
        purpose="registration",
        otp_hash=hash_otp("222222"),
        expires_at=now - timedelta(seconds=1),  # Expired
        attempts=0,
    )
    db_session.add(pending)
    db_session.add(challenge)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/register/verify",
        json={"email": "charlie@example.com", "otp": "222222"},
    )

    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()

    db_session.refresh(challenge)
    assert challenge.consumed_at is not None


def test_reused_otp_rejection(client, db_session):
    """Reusing an already consumed OTP returns 400."""
    now = datetime.now(timezone.utc)
    challenge = OTPChallenge(
        email="consumed@example.com",
        purpose="registration",
        otp_hash=hash_otp("333333"),
        expires_at=now + timedelta(minutes=5),
        attempts=1,
        consumed_at=now,
    )
    db_session.add(challenge)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/register/verify",
        json={"email": "consumed@example.com", "otp": "333333"},
    )

    assert response.status_code == 400


def test_maximum_otp_attempts_lockout(client, db_session):
    """Reaching maximum attempts consumes OTP challenge and rejects further tries."""
    now = datetime.now(timezone.utc)
    pending = PendingRegistration(
        name="Dave",
        email="dave@example.com",
        password_hash=hash_password("Secret123!"),
        expires_at=now + timedelta(minutes=15),
    )
    challenge = OTPChallenge(
        email="dave@example.com",
        purpose="registration",
        otp_hash=hash_otp("444444"),
        expires_at=now + timedelta(minutes=5),
        attempts=OTP_MAX_ATTEMPTS - 1,  # 4 attempts already
    )
    db_session.add(pending)
    db_session.add(challenge)
    db_session.commit()

    # 5th failed attempt
    res1 = client.post(
        "/api/v1/auth/register/verify",
        json={"email": "dave@example.com", "otp": "000000"},
    )
    assert res1.status_code == 400

    db_session.refresh(challenge)
    assert challenge.attempts == OTP_MAX_ATTEMPTS
    assert challenge.consumed_at is not None

    # Even submitting correct OTP afterwards fails
    res2 = client.post(
        "/api/v1/auth/register/verify",
        json={"email": "dave@example.com", "otp": "444444"},
    )
    assert res2.status_code == 400


# ---------------------------------------------------------------------------
# 3. OTP RATE LIMITING & COOLDOWN TESTS
# ---------------------------------------------------------------------------

def test_otp_resend_cooldown_raises_429(client, db_session):
    """Requesting OTP again within cooldown period returns 429 Too Many Requests."""
    now = datetime.now(timezone.utc)
    pending = PendingRegistration(
        name="Eve",
        email="eve@example.com",
        password_hash=hash_password("Secret123!"),
        expires_at=now + timedelta(minutes=15),
    )
    challenge = OTPChallenge(
        email="eve@example.com",
        purpose="registration",
        otp_hash=hash_otp("555555"),
        expires_at=now + timedelta(minutes=5),
        created_at=now - timedelta(seconds=10),  # Only 10s ago (< 60s cooldown)
    )
    db_session.add(pending)
    db_session.add(challenge)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/register/resend",
        json={"email": "eve@example.com"},
    )

    assert response.status_code == 429
    assert "wait" in response.json()["detail"].lower()


def test_otp_hourly_limit_raises_429(client, db_session):
    """Exceeding hourly OTP request limit returns 429 Too Many Requests."""
    now = datetime.now(timezone.utc)
    pending = PendingRegistration(
        name="Frank",
        email="frank@example.com",
        password_hash=hash_password("Secret123!"),
        expires_at=now + timedelta(minutes=15),
    )
    db_session.add(pending)

    # Add 5 challenges created within the past hour, older than cooldown
    for i in range(OTP_MAX_REQUESTS_PER_HOUR):
        c = OTPChallenge(
            email="frank@example.com",
            purpose="registration",
            otp_hash=hash_otp(f"10000{i}"),
            expires_at=now + timedelta(minutes=5),
            created_at=now - timedelta(minutes=10 + i * 5),
            consumed_at=now,
        )
        db_session.add(c)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/register/resend",
        json={"email": "frank@example.com"},
    )

    assert response.status_code == 429
    assert "limit" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 4. EMAIL EXCEPTION PRESERVATION & CLEANUP TESTS
# ---------------------------------------------------------------------------

def test_cooldown_exception_preservation_not_masked_as_503(client, db_session):
    """Cooldown error in start_registration must return 429 and NOT get masked as 503."""
    now = datetime.now(timezone.utc)
    challenge = OTPChallenge(
        email="cooldown@example.com",
        purpose="registration",
        otp_hash=hash_otp("666666"),
        expires_at=now + timedelta(minutes=5),
        created_at=now - timedelta(seconds=15),
    )
    db_session.add(challenge)
    db_session.commit()

    # User attempts to start registration
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Cooldown Test",
            "email": "cooldown@example.com",
            "password": "Password123!",
        },
    )

    # Must be 429 Too Many Requests, NOT 503 Service Unavailable!
    assert response.status_code == 429
    assert "wait" in response.json()["detail"].lower()

    # Pending registration must be cleaned up, not left orphaned
    pending = db_session.scalar(
        select(PendingRegistration).where(
            PendingRegistration.email == "cooldown@example.com"
        )
    )
    assert pending is None


def test_cleanup_after_email_failure_registration(client, db_session):
    """When Resend email delivery fails during registration, clean up and return 503."""
    with patch("backend.services.registration_service.send_email") as mock_email:
        mock_email.side_effect = RuntimeError("Resend API down")

        response = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Email Fail User",
                "email": "fail@example.com",
                "password": "Password123!",
            },
        )

        assert response.status_code == 503
        assert "could not be sent" in response.json()["detail"].lower()

        # PendingRegistration must be removed
        pending = db_session.scalar(
            select(PendingRegistration).where(
                PendingRegistration.email == "fail@example.com"
            )
        )
        assert pending is None

        # Challenge that failed to deliver must be deleted
        challenge = db_session.scalar(
            select(OTPChallenge).where(OTPChallenge.email == "fail@example.com")
        )
        assert challenge is None


def test_resend_email_failure_preserves_pending_and_older_otp(client, db_session):
    """Resend email failure must NOT delete pending registration and must NOT consume older valid OTP."""
    now = datetime.now(timezone.utc)
    pending = PendingRegistration(
        name="Resend User",
        email="resend@example.com",
        password_hash=hash_password("Password123!",),
        expires_at=now + timedelta(minutes=15),
    )
    older_challenge = OTPChallenge(
        email="resend@example.com",
        purpose="registration",
        otp_hash=hash_otp("777777"),
        expires_at=now + timedelta(minutes=4),
        created_at=now - timedelta(seconds=70),  # > 60s cooldown
        consumed_at=None,
    )
    db_session.add(pending)
    db_session.add(older_challenge)
    db_session.commit()

    with patch("backend.services.registration_service.send_email") as mock_email:
        mock_email.side_effect = RuntimeError("Resend network error")

        response = client.post(
            "/api/v1/auth/register/resend",
            json={"email": "resend@example.com"},
        )

        assert response.status_code == 503

        # Pending registration is preserved
        pending_check = db_session.scalar(
            select(PendingRegistration).where(
                PendingRegistration.email == "resend@example.com"
            )
        )
        assert pending_check is not None

        # Older valid OTP was NOT consumed
        db_session.refresh(older_challenge)
        assert older_challenge.consumed_at is None


def test_resend_otp_success_invalidates_previous_challenge(client, db_session):
    """Successful resend delivers new OTP and invalidates older unused challenge."""
    now = datetime.now(timezone.utc)
    pending = PendingRegistration(
        name="Resend Success",
        email="success@example.com",
        password_hash=hash_password("Password123!"),
        expires_at=now + timedelta(minutes=15),
    )
    older_challenge = OTPChallenge(
        email="success@example.com",
        purpose="registration",
        otp_hash=hash_otp("888888"),
        expires_at=now + timedelta(minutes=4),
        created_at=now - timedelta(seconds=70),
        consumed_at=None,
    )
    db_session.add(pending)
    db_session.add(older_challenge)
    db_session.commit()

    with patch("backend.services.registration_service.send_email") as mock_email:
        mock_email.return_value = {"success": True, "message_id": "msg_789"}

        response = client.post(
            "/api/v1/auth/register/resend",
            json={"email": "success@example.com"},
        )

        assert response.status_code == 202
        assert response.json()["success"] is True

        # Older challenge is now consumed
        db_session.refresh(older_challenge)
        assert older_challenge.consumed_at is not None

        # New challenge exists and is unconsumed
        new_challenge = db_session.scalar(
            select(OTPChallenge)
            .where(
                OTPChallenge.email == "success@example.com",
                OTPChallenge.consumed_at.is_(None),
            )
        )
        assert new_challenge is not None
        assert new_challenge.id != older_challenge.id


# ---------------------------------------------------------------------------
# 5. AUTHENTICATION & JWT TESTS
# ---------------------------------------------------------------------------

def test_successful_login(client, db_session):
    """Logging in with correct credentials returns 200 and Bearer access token."""
    user = User(
        name="Grace Hopper",
        email="grace@example.com",
        password_hash=hash_password("Compiler1952!"),
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "grace@example.com", "password": "Compiler1952!"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    payload = decode_access_token(data["access_token"])
    assert payload["sub"] == str(user.id)


def test_login_incorrect_password(client, db_session):
    """Logging in with incorrect password returns 401 Unauthorized."""
    user = User(
        name="Grace Hopper",
        email="grace2@example.com",
        password_hash=hash_password("Compiler1952!"),
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "grace2@example.com", "password": "WrongPassword!"},
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_nonexistent_user(client):
    """Logging in with non-existent email returns 401 Unauthorized."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "ghost@example.com", "password": "Password123!"},
    )

    assert response.status_code == 401


def test_protected_endpoint_me_success(client, db_session):
    """GET /api/v1/auth/me with valid Bearer token returns current user profile."""
    user = User(
        name="Ada Lovelace",
        email="ada@example.com",
        password_hash=hash_password("FirstProgrammer!"),
    )
    db_session.add(user)
    db_session.commit()

    token = create_access_token(user.id)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["name"] == "Ada Lovelace"
    assert data["email"] == "ada@example.com"


def test_protected_endpoint_invalid_token(client):
    """GET /api/v1/auth/me with malformed token returns 401."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert response.status_code == 401


def test_protected_endpoint_expired_token(client, db_session):
    """GET /api/v1/auth/me with expired token returns 401."""
    import jwt

    user = User(
        name="Test",
        email="expired_token@example.com",
        password_hash=hash_password("Password123!"),
    )
    db_session.add(user)
    db_session.commit()

    past = datetime.now(timezone.utc) - timedelta(hours=1)
    expired_token = jwt.encode(
        {"sub": str(user.id), "iat": past - timedelta(minutes=30), "exp": past},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


def test_protected_endpoint_missing_token(client):
    """GET /api/v1/auth/me without Authorization header returns 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_protected_endpoint_user_deleted(client, db_session):
    """Token for a user ID that no longer exists returns 401."""
    token = create_access_token(999999)
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
