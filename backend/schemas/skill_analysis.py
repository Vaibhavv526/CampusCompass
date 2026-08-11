from pydantic import BaseModel
from typing import List


class SkillInput(BaseModel):
    name: str
    proficiency: int
    strengths: str
    weak_areas: str
    experience: str


class SkillAnalysisInput(BaseModel):
    skills: List[SkillInput]