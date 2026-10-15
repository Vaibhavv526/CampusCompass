from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.auth.dependencies import get_current_user
from backend.models.user import User
from models.skill import Skill
from models.student import StudentProfile
from models.assessment_schema import LearningAssessmentResponse
from orchestrator import StudentMentorOrchestrator

from backend.schemas.student import StudentInput


router = APIRouter(
    prefix="/api/roadmap",
    tags=["Roadmap"],
)


class RoadmapRequest(BaseModel):
    student: StudentInput
    assessment: LearningAssessmentResponse


@router.post("")
def create_roadmap(
    request: RoadmapRequest,
    current_user: User = Depends(get_current_user),
):
    student = StudentProfile(
        name=request.student.name,
        email=request.student.email,
        degree=request.student.degree,
        branch=request.student.branch,
        current_year=request.student.current_year,
        semester=request.student.semester,
        career_goal=request.student.career_goal,
        interests=request.student.interests,
        weekly_hours=request.student.weekly_hours,
        skills=[
            Skill(
                skill.name,
                skill.category,
                skill.current_level,
                skill.target_level,
            )
            for skill in request.student.skills
        ],
    )

    orchestrator = StudentMentorOrchestrator(
        student=student,
        topic="General",
    )

    result = orchestrator.generate_roadmap(
        assessment=request.assessment
    )

    return result
