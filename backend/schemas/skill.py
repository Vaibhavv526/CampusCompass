from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    proficiency: int = Field(ge=0, le=100)
    strengths: str | None = Field(default=None, max_length=1000)
    weak_areas: str | None = Field(default=None, max_length=1000)
    experience: str | None = Field(default=None, max_length=1000)


class SkillUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    proficiency: int = Field(ge=0, le=100)
    strengths: str | None = Field(default=None, max_length=1000)
    weak_areas: str | None = Field(default=None, max_length=1000)
    experience: str | None = Field(default=None, max_length=1000)


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
