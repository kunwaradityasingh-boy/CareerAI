"""
End-to-end integration verification sequence according to Phase 6 requirements.
Executes the exact 14-step sequence in a safe isolated test environment.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database import get_db
from backend.models import User, PendingRegistration, OTPChallenge
from backend.services.otp_service import hash_otp


@pytest.fixture
def integration_env():
    """Isolated in-memory test environment."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine)
    PendingRegistration.__table__.create(engine)
    OTPChallenge.__table__.create(engine)

    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    yield {"client": client, "db": session}

    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def test_full_14_step_integration_sequence(integration_env):
    client = integration_env["client"]
    db = integration_env["db"]

    test_name = "Integration Tester"
    test_email = "integ_tester@example.com"
    test_password = "CareerAIPassword2026!"

    with patch("backend.services.registration_service.send_email") as mock_email:
        mock_email.return_value = {"success": True, "message_id": "mock_seq_001"}

        # -------------------------------------------------------------------
        # Step 1: Submit a new registration
        # -------------------------------------------------------------------
        reg_response = client.post(
            "/api/v1/auth/register",
            json={
                "name": test_name,
                "email": test_email,
                "password": test_password,
            },
        )
        assert reg_response.status_code == 202
        assert reg_response.json()["success"] is True

        # -------------------------------------------------------------------
        # Step 2: Verify pending registration creation
        # -------------------------------------------------------------------
        pending = db.scalar(
            select(PendingRegistration).where(PendingRegistration.email == test_email)
        )
        assert pending is not None, "PendingRegistration was not created"
        assert pending.name == test_name
        assert pending.email == test_email
        assert pending.password_hash != test_password  # Must be hashed

        # -------------------------------------------------------------------
        # Step 3: Verify OTP challenge creation
        # -------------------------------------------------------------------
        challenge = db.scalar(
            select(OTPChallenge)
            .where(OTPChallenge.email == test_email)
            .order_by(OTPChallenge.created_at.desc())
        )
        assert challenge is not None, "OTPChallenge was not created"
        assert challenge.purpose == "registration"
        assert challenge.consumed_at is None
        assert challenge.attempts == 0

        # -------------------------------------------------------------------
        # Step 4: Verify mocked email delivery
        # -------------------------------------------------------------------
        assert mock_email.called, "send_email was not called"
        call_kwargs = mock_email.call_args.kwargs
        assert call_kwargs["to_email"] == test_email
        assert "CareerAI - Email Verification Code" in call_kwargs["subject"]

        # Extract the raw OTP from the email HTML template to verify it matches hash
        raw_otp = None
        for code in range(1000000):
            candidate = f"{code:06d}"
            if hash_otp(candidate) == challenge.otp_hash:
                raw_otp = candidate
                break
        assert raw_otp is not None, "Could not reverse hash (HMAC mismatch)"
        assert raw_otp in call_kwargs["html_content"], "Raw OTP was not in email"

        # -------------------------------------------------------------------
        # Step 5: Submit correct OTP
        # -------------------------------------------------------------------
        verify_response = client.post(
            "/api/v1/auth/register/verify",
            json={
                "email": test_email,
                "otp": raw_otp,
            },
        )
        assert verify_response.status_code == 201

        # -------------------------------------------------------------------
        # Step 6: Verify permanent User creation
        # -------------------------------------------------------------------
        permanent_user = db.scalar(
            select(User).where(User.email == test_email)
        )
        assert permanent_user is not None, "Permanent User was not created"
        assert permanent_user.name == test_name
        assert permanent_user.email == test_email

        # -------------------------------------------------------------------
        # Step 7: Verify pending registration removal
        # -------------------------------------------------------------------
        pending_after = db.scalar(
            select(PendingRegistration).where(PendingRegistration.email == test_email)
        )
        assert pending_after is None, "PendingRegistration was not removed"

        # -------------------------------------------------------------------
        # Step 8: Verify OTP consumption
        # -------------------------------------------------------------------
        db.refresh(challenge)
        assert challenge.consumed_at is not None, "OTPChallenge was not consumed"

        # -------------------------------------------------------------------
        # Step 9: Login using the registered credentials
        # -------------------------------------------------------------------
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_email,
                "password": test_password,
            },
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        assert "access_token" in tokens
        access_token = tokens["access_token"]

        # -------------------------------------------------------------------
        # Step 10: Fetch /api/v1/auth/me
        # -------------------------------------------------------------------
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["id"] == permanent_user.id
        assert me_data["email"] == test_email
        assert me_data["name"] == test_name

        # -------------------------------------------------------------------
        # Step 11: Verify Dashboard access
        # -------------------------------------------------------------------
        # Protected endpoints succeed with valid bearer token
        assert me_response.status_code == 200
        # And fail without bearer token
        unauth_response = client.get("/api/v1/auth/me")
        assert unauth_response.status_code == 401

        # -------------------------------------------------------------------
        # Step 12: Test invalid and expired OTP cases
        # -------------------------------------------------------------------
        # Create an expired pending registration and challenge for test
        expired_email = "expired_case@example.com"
        now = datetime.now(timezone.utc)
        exp_pending = PendingRegistration(
            name="Exp",
            email=expired_email,
            password_hash="hash",
            expires_at=now + timedelta(minutes=15),
        )
        exp_challenge = OTPChallenge(
            email=expired_email,
            purpose="registration",
            otp_hash=hash_otp("123123"),
            expires_at=now - timedelta(seconds=1),  # Expired
            attempts=0,
        )
        db.add(exp_pending)
        db.add(exp_challenge)
        db.commit()

        # Expired OTP returns 400
        exp_res = client.post(
            "/api/v1/auth/register/verify",
            json={"email": expired_email, "otp": "123123"},
        )
        assert exp_res.status_code == 400
        assert "expired" in exp_res.json()["detail"].lower()

        # Invalid OTP returns 400
        valid_pending = PendingRegistration(
            name="Valid",
            email="invalid_case@example.com",
            password_hash="hash",
            expires_at=now + timedelta(minutes=15),
        )
        valid_challenge = OTPChallenge(
            email="invalid_case@example.com",
            purpose="registration",
            otp_hash=hash_otp("654321"),
            expires_at=now + timedelta(minutes=5),
            attempts=0,
        )
        db.add(valid_pending)
        db.add(valid_challenge)
        db.commit()

        inv_res = client.post(
            "/api/v1/auth/register/verify",
            json={"email": "invalid_case@example.com", "otp": "000000"},
        )
        assert inv_res.status_code == 400
        assert "incorrect" in inv_res.json()["detail"].lower()

        # -------------------------------------------------------------------
        # Step 13: Test cooldown and hourly limits
        # -------------------------------------------------------------------
        # Cooldown check
        cooldown_email = "cooldown_case@example.com"
        cd_pending = PendingRegistration(
            name="CD",
            email=cooldown_email,
            password_hash="hash",
            expires_at=now + timedelta(minutes=15),
        )
        cd_challenge = OTPChallenge(
            email=cooldown_email,
            purpose="registration",
            otp_hash=hash_otp("112233"),
            expires_at=now + timedelta(minutes=5),
            created_at=now - timedelta(seconds=20),  # < 60s
        )
        db.add(cd_pending)
        db.add(cd_challenge)
        db.commit()

        cd_res = client.post(
            "/api/v1/auth/register/resend",
            json={"email": cooldown_email},
        )
        assert cd_res.status_code == 429
        assert "wait" in cd_res.json()["detail"].lower()

        # Hourly limit check
        limit_email = "limit_case@example.com"
        lim_pending = PendingRegistration(
            name="Lim",
            email=limit_email,
            password_hash="hash",
            expires_at=now + timedelta(minutes=15),
        )
        db.add(lim_pending)
        for i in range(5):
            db.add(OTPChallenge(
                email=limit_email,
                purpose="registration",
                otp_hash=hash_otp(f"55555{i}"),
                expires_at=now + timedelta(minutes=5),
                created_at=now - timedelta(minutes=10 + i * 5),
                consumed_at=now,
            ))
        db.commit()

        lim_res = client.post(
            "/api/v1/auth/register/resend",
            json={"email": limit_email},
        )
        assert lim_res.status_code == 429
        assert "limit" in lim_res.json()["detail"].lower()

        # -------------------------------------------------------------------
        # Step 14: Test duplicate registration
        # -------------------------------------------------------------------
        # Trying to register again with test_email (which was permanently created in step 6)
        dup_res = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Imposter",
                "email": test_email,
                "password": "AnotherPassword123!",
            },
        )
        assert dup_res.status_code == 409
        assert "already exists" in dup_res.json()["detail"].lower()
