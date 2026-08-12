from pydantic import BaseModel, Field
from typing import List


class RecommendationResource(BaseModel):
    """Learning resource recommended for the student."""

    title: str
    link: str
    type: str


class RecommendationResponse(BaseModel):
    """Personalized recommendations for a student."""

    summary: str
    recommended_skills: List[str] = Field(default_factory=list)
    recommended_projects: List[str] = Field(default_factory=list)
    recommended_resources: List[RecommendationResource] = Field(
        default_factory=list
    )
    next_steps: List[str] = Field(default_factory=list)