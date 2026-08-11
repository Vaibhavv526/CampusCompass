from pydantic import BaseModel
from typing import List


class SkillAnalysis(BaseModel):
    name: str
    proficiency: float
    strengths: List[str]
    weak_areas: List[str]
    gap: str
    next_steps: List[str]


class SkillAnalysisResponse(BaseModel):
    summary: str
    skills: List[SkillAnalysis]