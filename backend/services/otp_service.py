from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from backend.core.config import (
    JWT_SECRET_KEY,
    OTP_LENGTH,
    OTP_EXPIRE_MINUTES,
    OTP_MAX_ATTEMPTS,
    OTP_RESEND_COOLDOWN_SECONDS,
    OTP_MAX_REQUESTS_PER_HOUR,
)
from backend.models import OTPChallenge


class OTPError(Exception):
    """Base exception for OTP operations."""


class OTPCooldownError(OTPError):
    pass


class OTPLimitError(OTPError):
    pass


class OTPExpiredError(OTPError):
    pass


class OTPInvalidError(OTPError):
    pass


def generate_otp() -> str:
    """Generate a cryptographically secure numeric OTP."""
    return f"{secrets.randbelow(10 ** OTP_LENGTH):0{OTP_LENGTH}d}"


def hash_otp(otp: str) -> str:
    """Create a keyed SHA-256 hash of the OTP."""
    if not isinstance(otp, str):
        raise ValueError("Invalid OTP.")

    if len(otp) != OTP_LENGTH or not otp.isdigit():
        raise ValueError("OTP must contain exactly 6 digits.")

    return hmac.new(
        JWT_SECRET_KEY.encode("utf-8"),
        otp.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_otp(otp: str, stored_hash: str) -> bool:
    """Verify OTP using constant-time comparison."""
    if not isinstance(otp, str) or not otp.isdigit():
        return False

    if len(otp) != OTP_LENGTH:
        return False

    if not isinstance(stored_hash, str):
        return False

    calculated_hash = hash_otp(otp)

    return hmac.compare_digest(calculated_hash, stored_hash)


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Ensure a datetime object is timezone-aware in UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def consume_previous_challenges(
    db: Session,
    email: str,
    purpose: str,
    exclude_id: int | None = None,
) -> None:
    """Invalidate previous unused challenges for an email and purpose."""
    normalized_email = email.strip().lower()
    now = datetime.now(timezone.utc)

    query = select(OTPChallenge).where(
        OTPChallenge.email == normalized_email,
        OTPChallenge.purpose == purpose,
        OTPChallenge.consumed_at.is_(None),
    )

    if exclude_id is not None:
        query = query.where(OTPChallenge.id != exclude_id)

    previous_challenges = db.scalars(query).all()

    for challenge in previous_challenges:
        challenge.consumed_at = now

    db.commit()


def create_otp_challenge(
    db: Session,
    email: str,
    purpose: str,
    user_id: int | None = None,
    consume_previous: bool = True,
) -> str:
    """
    Create and persist an OTP challenge.

    Returns the raw OTP only to the internal caller,
    which must send it through the email service.
    """

    normalized_email = email.strip().lower()
    now = datetime.now(timezone.utc)

    if not normalized_email:
        raise ValueError("Email is required.")

    if not purpose or len(purpose) > 30:
        raise ValueError("Invalid OTP purpose.")

    try:
        # Check the latest OTP request for cooldown.
        latest_challenge = db.scalar(
            select(OTPChallenge)
            .where(
                OTPChallenge.email == normalized_email,
                OTPChallenge.purpose == purpose,
            )
            .order_by(OTPChallenge.created_at.desc())
            .limit(1)
        )

        if latest_challenge and latest_challenge.created_at:
            elapsed = (now - ensure_utc(latest_challenge.created_at)).total_seconds()

            if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
                raise OTPCooldownError("Please wait before requesting another OTP.")

        # Enforce hourly request limit.
        one_hour_ago = now - timedelta(hours=1)

        request_count = db.scalar(
            select(func.count())
            .select_from(OTPChallenge)
            .where(
                OTPChallenge.email == normalized_email,
                OTPChallenge.purpose == purpose,
                OTPChallenge.created_at >= one_hour_ago,
            )
        )

        if request_count >= OTP_MAX_REQUESTS_PER_HOUR:
            raise OTPLimitError("OTP request limit reached. Try again later.")

        if consume_previous:
            # Invalidate previous unused challenges immediately.
            consume_previous_challenges(
                db=db,
                email=normalized_email,
                purpose=purpose,
            )

        raw_otp = generate_otp()

        challenge = OTPChallenge(
            user_id=user_id,
            email=normalized_email,
            purpose=purpose,
            otp_hash=hash_otp(raw_otp),
            expires_at=now + timedelta(minutes=OTP_EXPIRE_MINUTES),
            attempts=0,
        )

        db.add(challenge)
        db.commit()

        return raw_otp

    except OTPError:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def verify_otp_challenge(
    db: Session,
    email: str,
    purpose: str,
    otp: str,
) -> bool:
    """
    Verify the latest unused OTP challenge.

    A challenge is consumed after successful verification,
    expiry, or reaching the maximum number of attempts.
    """

    normalized_email = email.strip().lower()
    now = datetime.now(timezone.utc)

    challenge = db.scalar(
        select(OTPChallenge)
        .where(
            OTPChallenge.email == normalized_email,
            OTPChallenge.purpose == purpose,
            OTPChallenge.consumed_at.is_(None),
        )
        .order_by(OTPChallenge.created_at.desc())
        .limit(1)
        .with_for_update()
    )

    if challenge is None:
        raise OTPInvalidError("Invalid or already used OTP.")

    if ensure_utc(challenge.expires_at) <= now:
        challenge.consumed_at = now
        db.commit()
        raise OTPExpiredError("OTP has expired. Request a new OTP.")

    if challenge.attempts >= OTP_MAX_ATTEMPTS:
        challenge.consumed_at = now
        db.commit()
        raise OTPInvalidError("Maximum OTP attempts exceeded.")

    if not verify_otp(otp, challenge.otp_hash):
        challenge.attempts += 1

        if challenge.attempts >= OTP_MAX_ATTEMPTS:
            challenge.consumed_at = now

        db.commit()

        raise OTPInvalidError("Incorrect OTP.")

    challenge.consumed_at = now
    db.commit()

    return True
