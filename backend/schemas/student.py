from pydantic import BaseModel, Field


class SkillInput(BaseModel):
    name: str
    category: str
    current_level: float = Field(ge=0, le=100)
    target_level: float = Field(ge=0, le=100)


class StudentInput(BaseModel):
    name: str
    email: str
    degree: str
    branch: str
    current_year: int
    semester: int
    career_goal: str
    interests: list[str] = []
    weekly_hours: float = Field(ge=0)
    skills: list[SkillInput] = []