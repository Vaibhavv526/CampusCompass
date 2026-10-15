from fastapi import APIRouter, Depends

from backend.auth.dependencies import get_current_user
from backend.models.user import User
from models.skill import Skill
from models.student import StudentProfile
from orchestrator import StudentMentorOrchestrator

from backend.schemas.student import StudentInput


router = APIRouter(
    prefix="/api/assessment",
    tags=["Assessment"],
)


@router.post("")
def create_assessment(
    student_data: StudentInput,
    current_user: User = Depends(get_current_user),
):
    student = StudentProfile(
        name=student_data.name,
        email=student_data.email,
        degree=student_data.degree,
        branch=student_data.branch,
        current_year=student_data.current_year,
        semester=student_data.semester,
        career_goal=student_data.career_goal,
        interests=student_data.interests,
        weekly_hours=student_data.weekly_hours,
        skills=[
            Skill(
                skill.name,
                skill.category,
                skill.current_level,
                skill.target_level,
            )
            for skill in student_data.skills
        ],
    )

    orchestrator = StudentMentorOrchestrator(
        student=student,
        topic="General",
    )

    result = orchestrator.assess_student()

    return result
