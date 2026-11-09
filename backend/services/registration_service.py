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
    consume_previous_challenges,
    verify_otp,
    ensure_utc,
    OTPInvalidError,
    OTPExpiredError,
    OTPCooldownError,
    OTPLimitError,
)
from backend.services.email_service import send_email

logger = logging.getLogger(__name__)


def _cleanup_pending_registration(db: Session, email: str) -> None:
    """Delete a pending registration for an email if one exists."""
    try:
        pending_record = db.scalar(
            select(PendingRegistration)
            .where(PendingRegistration.email == email)
            .with_for_update()
        )
        if pending_record:
            db.delete(pending_record)
            db.commit()
    except Exception:
        db.rollback()


def _cleanup_failed_registration(db: Session, email: str) -> None:
    """Clean up pending registration and undelivered OTP challenge after email failure."""
    try:
        pending_record = db.scalar(
            select(PendingRegistration)
            .where(PendingRegistration.email == email)
            .with_for_update()
        )
        if pending_record:
            db.delete(pending_record)

        latest_challenge = db.scalar(
            select(OTPChallenge)
            .where(
                OTPChallenge.email == email,
                OTPChallenge.purpose == "registration",
                OTPChallenge.consumed_at.is_(None),
            )
            .order_by(OTPChallenge.created_at.desc())
            .limit(1)
            .with_for_update()
        )
        if latest_challenge:
            db.delete(latest_challenge)

        db.commit()
    except Exception:
        logger.exception("Failed to clean up registration records.")
        db.rollback()


def _build_otp_email_html(safe_name: str, otp: str) -> str:
    """Construct HTML email template for registration OTP."""
    return f"""
    <div style="
        font-family:Arial,sans-serif;
        max-width:520px;
        margin:auto;
    ">
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

        <p>
            If you did not request this code,
            please ignore this email.
        </p>

        <p>CareerAI Team</p>
    </div>
    """


def start_registration(
    db: Session,
    name: str,
    email: str,
    password: str,
) -> dict:
    """
    Start a new registration.

    1. Validate user details.
    2. Reject an existing permanent account (409).
    3. Create a pending registration.
    4. Generate an OTP challenge.
    5. Send the OTP email.

    A permanent User is created only after successful OTP verification.
    """

    normalized_email = email.strip().lower()
    normalized_name = name.strip()

    if len(normalized_name) < 2 or len(normalized_name) > 100:
        raise ValueError("Name must contain between 2 and 100 characters.")

    if len(password) < 8 or len(password) > 128:
        raise ValueError("Password must contain 8–128 characters.")

    # Reject an already registered account.
    existing_user = db.scalar(select(User).where(User.email == normalized_email))

    if existing_user:
        raise ValueError("An account with this email already exists. Please sign in.")

    now = datetime.now(timezone.utc)

    # Create pending registration.
    try:
        existing_pending = db.scalar(
            select(PendingRegistration)
            .where(PendingRegistration.email == normalized_email)
            .with_for_update()
        )

        if existing_pending:
            if ensure_utc(existing_pending.expires_at) > now:
                raise ValueError(
                    "A registration is already pending for this email. "
                    "Please complete verification or try again after it expires."
                )

            # Remove only an expired pending registration.
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

    # Generate OTP without consuming previous challenges until email succeeds.
    try:
        otp = create_otp_challenge(
            db=db,
            email=normalized_email,
            purpose="registration",
            consume_previous=False,
        )
    except (OTPCooldownError, OTPLimitError):
        # Rate-limit exceptions must NOT be converted into generic email errors.
        db.rollback()
        _cleanup_pending_registration(db, normalized_email)
        raise

    # Send email.
    try:
        safe_name = escape(normalized_name)
        html_content = _build_otp_email_html(safe_name, otp)

        send_email(
            to_email=normalized_email,
            subject="CareerAI - Email Verification Code",
            html_content=html_content,
        )

        # Invalidate previous unused challenges now that email was accepted.
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
            consume_previous_challenges(
                db=db,
                email=normalized_email,
                purpose="registration",
                exclude_id=latest_challenge.id,
            )

        return {
            "success": True,
            "message": "Verification code sent to your email.",
            "email": normalized_email,
        }

    except Exception as error:
        logger.exception("Registration email delivery failed.")
        db.rollback()
        _cleanup_failed_registration(db, normalized_email)
        raise RuntimeError(
            f"Registration email could not be sent: {error}"
        ) from error


def resend_registration_otp(
    db: Session,
    email: str,
) -> dict:
    """
    Resend OTP for an existing active pending registration.
    """
    normalized_email = email.strip().lower()
    now = datetime.now(timezone.utc)

    if not normalized_email:
        raise ValueError("Email is required.")

    # Reject an already registered account.
    existing_user = db.scalar(select(User).where(User.email == normalized_email))
    if existing_user:
        raise ValueError("An account with this email already exists. Please sign in.")

    # Check active pending registration.
    pending = db.scalar(
        select(PendingRegistration)
        .where(PendingRegistration.email == normalized_email)
    )
    if not pending or ensure_utc(pending.expires_at) <= now:
        raise ValueError("No active registration found for this email. Please register again.")

    # Create new OTP challenge without consuming previous challenges yet.
    try:
        otp = create_otp_challenge(
            db=db,
            email=normalized_email,
            purpose="registration",
            consume_previous=False,
        )
    except (OTPCooldownError, OTPLimitError):
        # Rate limit/cooldown exceptions propagate directly.
        raise

    try:
        safe_name = escape(pending.name)
        html_content = _build_otp_email_html(safe_name, otp)

        send_email(
            to_email=normalized_email,
            subject="CareerAI - Email Verification Code",
            html_content=html_content,
        )

        # Invalidate previous unused challenges now that email was accepted.
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
            consume_previous_challenges(
                db=db,
                email=normalized_email,
                purpose="registration",
                exclude_id=latest_challenge.id,
            )

        return {
            "success": True,
            "message": "Verification code resent to your email.",
            "email": normalized_email,
        }

    except Exception as error:
        logger.exception("Resend OTP email delivery failed.")
        db.rollback()

        # Clean up ONLY the latest undelivered challenge.
        # Pending registration and older valid challenges are preserved.
        try:
            latest_challenge = db.scalar(
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
            if latest_challenge:
                db.delete(latest_challenge)
                db.commit()
        except Exception:
            db.rollback()

        raise RuntimeError(
            f"Verification email could not be sent: {error}"
        ) from error


def verify_registration(
    db: Session,
    email: str,
    otp: str,
) -> User:
    """
    Verify registration OTP and create the permanent User.

    The permanent user creation, OTP consumption and pending
    registration removal are committed atomically.
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
            raise OTPInvalidError("Registration request not found. Please register again.")

        # Check pending registration expiry.
        if ensure_utc(pending.expires_at) <= now:
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

        # Lock latest unused registration OTP.
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
        if ensure_utc(challenge.expires_at) <= now:
            challenge.consumed_at = now
            db.commit()

            raise OTPExpiredError("OTP expired. Please request a new OTP.")

        # Check maximum attempts.
        if challenge.attempts >= OTP_MAX_ATTEMPTS:
            challenge.consumed_at = now
            db.commit()

            raise OTPInvalidError("Maximum OTP attempts exceeded.")

        # Verify OTP.
        if not verify_otp(otp, challenge.otp_hash):
            challenge.attempts += 1

            if challenge.attempts >= OTP_MAX_ATTEMPTS:
                challenge.consumed_at = now

            db.commit()

            raise OTPInvalidError("Incorrect OTP.")

        # Final duplicate account check.
        existing_user = db.scalar(select(User).where(User.email == normalized_email))

        if existing_user:
            raise ValueError(
                "An account with this email already exists. Please sign in."
            )

        # Create permanent user.
        user = User(
            name=pending.name,
            email=pending.email,
            password_hash=pending.password_hash,
        )

        db.add(user)

        # Consume OTP and remove pending registration.
        challenge.consumed_at = now
        db.delete(pending)

        # Commit all changes together atomically.
        db.commit()
        db.refresh(user)

        return user

    except (OTPInvalidError, OTPExpiredError):
        raise

    except Exception:
        db.rollback()
        raise
