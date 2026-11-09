import jwt

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas.auth import (
    RegisterRequest,
    RegistrationStartResponse,
    OTPVerifyRequest,
    UserResponse,
    TokenResponse,
)
from backend.services.auth_service import authenticate_user
from backend.services.registration_service import (
    start_registration,
    verify_registration,
)
from backend.services.otp_service import (
    OTPInvalidError,
    OTPExpiredError,
    OTPCooldownError,
    OTPLimitError,
)
from backend.core.security import (
    create_access_token,
    decode_access_token,
)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# --------------------------------------------------
# 1. START REGISTRATION
# --------------------------------------------------


@router.post(
    "/register",
    response_model=RegistrationStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    try:
        return start_registration(
            db=db,
            name=payload.name,
            email=str(payload.email),
            password=payload.password,
        )

    except (OTPCooldownError, OTPLimitError) as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration email could not be sent. Please try again later.",
        ) from exc


# --------------------------------------------------
# 2. VERIFY REGISTRATION OTP
# --------------------------------------------------


@router.post(
    "/register/verify",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def verify_registration_endpoint(
    payload: OTPVerifyRequest,
    db: Session = Depends(get_db),
):
    try:
        return verify_registration(
            db=db,
            email=str(payload.email),
            otp=payload.otp,
        )

    except (OTPExpiredError, OTPInvalidError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration could not be completed.",
        ) from exc


# --------------------------------------------------
# 3. LOGIN
# --------------------------------------------------


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        db,
        form.username,
        form.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }


# --------------------------------------------------
# 4. GET CURRENT AUTHENTICATED USER
# --------------------------------------------------


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])

        if user_id <= 0:
            raise ValueError("Invalid user ID")

    except (
        jwt.InvalidTokenError,
        ValueError,
        TypeError,
        KeyError,
    ):
        raise credentials_error

    user = db.get(User, user_id)

    if user is None:
        raise credentials_error

    return user


# --------------------------------------------------
# 5. CURRENT USER PROFILE
# --------------------------------------------------


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user
