from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import User
from backend.core.security import hash_password, verify_password


def register_user(
    db: Session,
    name: str,
    email: str,
    password: str,
) -> User:
    normalized_email = email.strip().lower()

    existing_user = db.scalar(select(User).where(User.email == normalized_email))

    if existing_user:
        raise ValueError("Email is already registered.")

    user = User(
        name=name.strip(),
        email=normalized_email,
        password_hash=hash_password(password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    normalized_email = email.strip().lower()

    user = db.scalar(select(User).where(User.email == normalized_email))

    if not user or not verify_password(
        password,
        user.password_hash,
    ):
        return None

    return user
