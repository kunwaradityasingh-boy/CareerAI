import logging
from datetime import datetime, timedelta, timezone
from html import escape

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.config import (
    PENDING_REGISTRATION_EXPIRE_MINUTES,
    OTP_MAX_ATTEMPTS,
)
from backend.models import User, PendingRegistration, OTPChallenge
from backend.core.security import hash_password
from backend.services.otp_service import (
    create_otp_challenge,
    verify_otp,
    OTPInvalidError,
    OTPExpiredError,
)
from backend.services.email_service import send_email

logger = logging.getLogger(__name__)


def start_registration(
    db: Session,
    name: str,
    email: str,
    password: str,
) -> dict:
    """
    Create a pending registration and send an email OTP.
    No permanent User account is created here.
    """

    normalized_email = email.strip().lower()
    normalized_name = name.strip()

    if len(normalized_name) < 2:
        raise ValueError("Name must contain at least 2 characters.")

    existing_user = db.scalar(select(User).where(User.email == normalized_email))

    if existing_user:
        raise ValueError("Unable to start registration with this email.")

    now = datetime.now(timezone.utc)

    try:
        existing_pending = db.scalar(
            select(PendingRegistration)
            .where(PendingRegistration.email == normalized_email)
            .with_for_update()
        )

        if existing_pending:
            if existing_pending.expires_at > now:
                raise ValueError("Registration is already pending. Request a new OTP.")

            db.delete(existing_pending)
            db.flush()

        pending = PendingRegistration(
            name=normalized_name,
            email=normalized_email,
            password_hash=hash_password(password),
            expires_at=now + timedelta(minutes=PENDING_REGISTRATION_EXPIRE_MINUTES),
        )

        db.add(pending)
        db.commit()

    except IntegrityError as error:
        db.rollback()
        raise ValueError(
            "A registration request already exists for this email."
        ) from error

    except Exception:
        db.rollback()
        raise

    try:
        otp = create_otp_challenge(
            db=db,
            email=normalized_email,
            purpose="registration",
        )

        safe_name = escape(normalized_name)

        html_content = f"""
        <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;">
            <h2>Verify your CareerAI email</h2>

            <p>Hello {safe_name},</p>

            <p>Your CareerAI registration verification code is:</p>

            <div style="
                font-size:32px;
                font-weight:bold;
                letter-spacing:8px;
                padding:16px;
                background:#f3f4f6;
                text-align:center;
                border-radius:8px;
            ">
                {otp}
            </div>

            <p>This code expires in 5 minutes.</p>

            <p>If you did not request this code, ignore this email.</p>

            <p>CareerAI Team</p>
        </div>
        """

        send_email(
            to_email=normalized_email,
            subject="CareerAI - Email Verification Code",
            html_content=html_content,
        )

        return {
            "success": True,
            "message": "Verification code sent to your email.",
            "email": normalized_email,
        }

    except Exception:
        # Log the actual OTP or email delivery error.
        logger.exception(
            "Registration OTP/email operation failed for %s",
            normalized_email,
        )

        # Clean up the pending registration and unused OTP.
        db.rollback()

        try:
            db.query(PendingRegistration).filter_by(email=normalized_email).delete(
                synchronize_session=False
            )

            latest_challenge = db.scalar(
                select(OTPChallenge)
                .where(
                    OTPChallenge.email == normalized_email,
                    OTPChallenge.purpose == "registration",
                    OTPChallenge.consumed_at.is_(None),
                )
                .order_by(OTPChallenge.created_at.desc())
                .limit(1)
            )

            if latest_challenge:
                latest_challenge.consumed_at = datetime.now(timezone.utc)

            db.commit()

        except Exception:
            logger.exception(
                "Registration cleanup failed for %s",
                normalized_email,
            )
            db.rollback()

        raise RuntimeError("Unable to send verification email. Please try again later.")


def verify_registration(
    db: Session,
    email: str,
    otp: str,
) -> User:
    """
    Verify registration OTP and create the permanent User
    within one database transaction.
    """

    normalized_email = email.strip().lower()
    now = datetime.now(timezone.utc)

    try:
        # Lock pending registration.
        pending = db.scalar(
            select(PendingRegistration)
            .where(PendingRegistration.email == normalized_email)
            .with_for_update()
        )

        if pending is None:
            raise ValueError("Registration request not found. Please register again.")

        # Check pending registration expiry.
        if pending.expires_at <= now:
            db.query(OTPChallenge).filter(
                OTPChallenge.email == normalized_email,
                OTPChallenge.purpose == "registration",
                OTPChallenge.consumed_at.is_(None),
            ).update(
                {"consumed_at": now},
                synchronize_session=False,
            )

            db.delete(pending)
            db.commit()

            raise OTPExpiredError("Registration expired. Please register again.")

        # Lock the latest unused registration OTP.
        challenge = db.scalar(
            select(OTPChallenge)
            .where(
                OTPChallenge.email == normalized_email,
                OTPChallenge.purpose == "registration",
                OTPChallenge.consumed_at.is_(None),
            )
            .order_by(OTPChallenge.created_at.desc())
            .limit(1)
            .with_for_update()
        )

        if challenge is None:
            raise OTPInvalidError("OTP not found. Please request a new OTP.")

        # Check OTP expiry.
        if challenge.expires_at <= now:
            challenge.consumed_at = now
            db.commit()

            raise OTPExpiredError("OTP expired. Please request a new OTP.")

        # Check maximum attempts.
        if challenge.attempts >= OTP_MAX_ATTEMPTS:
            challenge.consumed_at = now
            db.commit()

            raise OTPInvalidError("Maximum OTP attempts exceeded.")

        # Verify OTP hash.
        if not verify_otp(otp, challenge.otp_hash):
            challenge.attempts += 1

            if challenge.attempts >= OTP_MAX_ATTEMPTS:
                challenge.consumed_at = now

            db.commit()

            raise OTPInvalidError("Incorrect OTP.")

        # Check duplicate permanent account.
        existing_user = db.scalar(select(User).where(User.email == normalized_email))

        if existing_user:
            raise ValueError("An account with this email already exists.")

        # Create permanent account.
        user = User(
            name=pending.name,
            email=pending.email,
            password_hash=pending.password_hash,
        )

        db.add(user)

        # Consume OTP and remove pending registration.
        challenge.consumed_at = now
        db.delete(pending)

        # Both changes commit atomically.
        db.commit()
        db.refresh(user)

        return user

    except (OTPInvalidError, OTPExpiredError):
        raise

    except Exception:
        db.rollback()
        raise
