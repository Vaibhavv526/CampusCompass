from fastapi import APIRouter, Depends

from backend.auth.dependencies import get_current_user
from backend.models.user import User
from agents.skill_analysis_agent import SkillAnalysisAgent
from backend.schemas.skill_analysis import SkillAnalysisInput

router = APIRouter(
    prefix="/api/skill-analysis",
    tags=["Skill Analysis"],
)


@router.post("")
def analyze_skills(
    request: SkillAnalysisInput,
    current_user: User = Depends(get_current_user),
):
    agent = SkillAnalysisAgent()

    result = agent.analyze(request.skills)

    return result
