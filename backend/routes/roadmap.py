from fastapi import APIRouter
from pydantic import BaseModel

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
def create_roadmap(request: RoadmapRequest):
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