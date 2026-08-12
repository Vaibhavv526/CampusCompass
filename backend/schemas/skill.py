from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    proficiency: int = Field(ge=0, le=100)
    strengths: str | None = None
    weak_areas: str | None = None
    experience: str | None = None
class SkillUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    proficiency: int = Field(ge=0, le=100)
    strengths: str | None = None
    weak_areas: str | None = None
    experience: str | None = None

class SkillResponse(BaseModel):
    id: int
    name: str
    proficiency: int
    strengths: str | None
    weak_areas: str | None
    experience: str | None

    model_config = {
        "from_attributes": True,
    }