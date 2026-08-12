from sqlalchemy.orm import Session

from backend.models.student_skill import StudentSkill
from backend.models.student_profile import StudentProfile
from backend.schemas.skill import SkillCreate, SkillUpdate

def get_student_profile(
    db: Session,
    user_id: int,
) -> StudentProfile | None:
    return (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == user_id)
        .first()
    )


def create_skill(
    db: Session,
    student_profile_id: int,
    skill_data: SkillCreate,
) -> StudentSkill:
    skill = StudentSkill(
        student_profile_id=student_profile_id,
        name=skill_data.name,
        proficiency=skill_data.proficiency,
        strengths=skill_data.strengths,
        weak_areas=skill_data.weak_areas,
        experience=skill_data.experience,
    )

    db.add(skill)
    db.commit()
    db.refresh(skill)

    return skill

def update_skill(
    db: Session,
    skill: StudentSkill,
    skill_data: SkillUpdate,
) -> StudentSkill:
    skill.name = skill_data.name
    skill.proficiency = skill_data.proficiency
    skill.strengths = skill_data.strengths
    skill.weak_areas = skill_data.weak_areas
    skill.experience = skill_data.experience

    db.commit()
    db.refresh(skill)

    return skill

def get_student_skills(
    db: Session,
    student_profile_id: int,
) -> list[StudentSkill]:
    return (
        db.query(StudentSkill)
        .filter(
            StudentSkill.student_profile_id
            == student_profile_id
        )
        .all()
    )