from backend.database import SessionLocal
from backend.models import OTPChallenge
from backend.services.otp_service import (
    create_otp_challenge,
    verify_otp_challenge,
    OTPInvalidError,
)

db = SessionLocal()
email = "otp-service-test@careerai.invalid"

try:
    otp = create_otp_challenge(db, email, "registration")
    print("OTP DATABASE INSERT: PASS")

    wrong_otp = "000000" if otp != "000000" else "111111"

    try:
        verify_otp_challenge(db, email, "registration", wrong_otp)
    except OTPInvalidError:
        print("WRONG OTP REJECTION: PASS")

    verify_otp_challenge(db, email, "registration", otp)
    print("CORRECT OTP VERIFICATION: PASS")

    challenge = db.query(OTPChallenge).filter_by(email=email).first()

    print("OTP CONSUMED:", challenge.consumed_at is not None)

finally:
    db.query(OTPChallenge).filter_by(email=email).delete()
    db.commit()
    db.close()
