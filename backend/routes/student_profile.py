from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.schemas.student_profile import (
    StudentProfileCreate,
    StudentProfileResponse,
)
from backend.services.student_profile_service import (
    create_student_profile,
    get_student_profile,
)


router = APIRouter(
    prefix="/api/student-profile",
    tags=["Student Profile"],
)


@router.post(
    "",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_profile(
    profile_data: StudentProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing_profile = get_student_profile(
        db,
        current_user.id,
    )

    if existing_profile is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student profile already exists.",
        )

    return create_student_profile(
        db=db,
        user=current_user,
        profile_data=profile_data,
    )


@router.get(
    "",
    response_model=StudentProfileResponse,
)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = get_student_profile(
        db,
        current_user.id,
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found.",
        )

    return profile