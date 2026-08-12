from sqlalchemy.orm import Session

from backend.models.student_profile import StudentProfile
from backend.models.user import User
from backend.schemas.student_profile import StudentProfileCreate


def get_student_profile(
    db: Session,
    user_id: int,
) -> StudentProfile | None:
    return (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == user_id)
        .first()
    )


def create_student_profile(
    db: Session,
    user: User,
    profile_data: StudentProfileCreate,
) -> StudentProfile:
    profile = StudentProfile(
        user_id=user.id,
        full_name=user.full_name,
        degree=profile_data.degree,
        branch=profile_data.branch,
        current_year=profile_data.current_year,
        semester=profile_data.semester,
        career_goal=profile_data.career_goal,
        interests=profile_data.interests,
        weekly_hours=profile_data.weekly_hours,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return profile