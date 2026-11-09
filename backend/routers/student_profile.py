from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.routers.auth import get_current_user
from backend.schemas.student_profile import (
    StudentProfileUpsert,
    StudentProfileResponse,
)
from backend.services.student_profile_service import (
    get_student_profile,
    upsert_student_profile,
)

router = APIRouter(
    prefix="/api/v1/students/me",
    tags=["Student Profile"],
)


@router.get(
    "/profile",
    response_model=StudentProfileResponse,
)
def read_student_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = get_student_profile(db, current_user.id)

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile has not been created yet.",
        )

    return profile


@router.put(
    "/profile",
    response_model=StudentProfileResponse,
)
def save_student_profile(
    payload: StudentProfileUpsert,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return upsert_student_profile(db, current_user, payload)

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile could not be saved because of a database conflict.",
        ) from exc
