from pydantic import BaseModel, Field


class StudentProfileCreate(BaseModel):
    degree: str = Field(min_length=1, max_length=100)
    branch: str = Field(min_length=1, max_length=100)
    current_year: int = Field(ge=1, le=10)
    semester: int = Field(ge=1, le=20)
    career_goal: str = Field(min_length=1, max_length=200)
    interests: str | None = None
    weekly_hours: int | None = Field(
        default=None,
        ge=1,
        le=168,
    )


class StudentProfileResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    degree: str
    branch: str
    current_year: int
    semester: int
    career_goal: str
    interests: str | None
    weekly_hours: int | None

    model_config = {
        "from_attributes": True,
    }