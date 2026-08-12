from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.schemas.skill import (
    SkillCreate,
    SkillResponse,
    SkillUpdate,
)
from backend.models.student_skill import StudentSkill
from backend.services.skill_service import (
    create_skill,
    get_student_profile,
    get_student_skills,
    update_skill,
)


router = APIRouter(
    prefix="/api/skills",
    tags=["Skills"],
)


@router.post(
    "",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_skill(
    skill_data: SkillCreate,
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

    return create_skill(
        db=db,
        student_profile_id=profile.id,
        skill_data=skill_data,
    )

@router.put(
    "/{skill_id}",
    response_model=SkillResponse,
)
def edit_skill(
    skill_id: int,
    skill_data: SkillUpdate,
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

    skill = (
        db.query(StudentSkill)
        .filter(
            StudentSkill.id == skill_id,
            StudentSkill.student_profile_id == profile.id,
        )
        .first()
    )

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found.",
        )

    return update_skill(
        db=db,
        skill=skill,
        skill_data=skill_data,
    )
@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_skill(
    skill_id: int,
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

    skill = (
        db.query(StudentSkill)
        .filter(
            StudentSkill.id == skill_id,
            StudentSkill.student_profile_id == profile.id,
        )
        .first()
    )

    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found.",
        )

    db.delete(skill)
    db.commit()

    return None

@router.get(
    "",
    response_model=list[SkillResponse],
)
def get_skills(
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

    return get_student_skills(
        db,
        profile.id,
    )