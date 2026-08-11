from fastapi import APIRouter

from agents.skill_analysis_agent import SkillAnalysisAgent
from backend.schemas.skill_analysis import SkillAnalysisInput

router = APIRouter(
    prefix="/api/skill-analysis",
    tags=["Skill Analysis"],
)


@router.post("")
def analyze_skills(request: SkillAnalysisInput):
    agent = SkillAnalysisAgent()

    result = agent.analyze(request.skills)

    return result