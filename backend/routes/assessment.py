from fastapi import APIRouter, Depends

from backend.auth.dependencies import get_current_user
from backend.core.rate_limit import rate_limit_user
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
    _rate_limit: None = Depends(rate_limit_user(max_requests=5, window_seconds=60, group="assessment")),
):
    student = StudentProfile(
        name=current_user.full_name,
        email=current_user.email,
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
