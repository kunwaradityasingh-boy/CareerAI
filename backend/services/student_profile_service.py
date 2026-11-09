from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import StudentProfile, User
from backend.schemas.student_profile import StudentProfileUpsert


def get_student_profile(
    db: Session,
    user_id: int,
) -> StudentProfile | None:
    statement = select(StudentProfile).where(StudentProfile.user_id == user_id)

    return db.scalar(statement)


def upsert_student_profile(
    db: Session,
    user: User,
    payload: StudentProfileUpsert,
) -> StudentProfile:
    profile = get_student_profile(db, user.id)

    profile_data = payload.model_dump()

    if profile is None:
        profile = StudentProfile(
            user_id=user.id,
            **profile_data,
        )
        db.add(profile)
    else:
        for field, value in profile_data.items():
            setattr(profile, field, value)

    try:
        db.commit()
        db.refresh(profile)
    except Exception:
        db.rollback()
        raise

    return profile
