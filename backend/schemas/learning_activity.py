from datetime import datetime
import json
from pydantic import BaseModel, Field, field_validator


class LearningActivityCreate(BaseModel):
    activity_type: str = Field(
        min_length=1,
        max_length=50,
        pattern=r"^(assessment|quiz|roadmap|tutor|practice)$",
    )
    title: str = Field(
        min_length=1,
        max_length=255,
    )
    summary: str | None = Field(
        default=None,
        max_length=1000,
    )
    score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )
    data: dict | None = Field(
        default=None,
    )

    @field_validator("data")
    @classmethod
    def validate_data_size(cls, v: dict | None) -> dict | None:
        if v is not None:
            try:
                serialized = json.dumps(v)
                if len(serialized) > 500000:
                    raise ValueError("Payload data exceeds maximum allowed size (500KB).")
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid JSON data payload: {e}")
        return v


class LearningActivityUpdate(BaseModel):
    summary: str | None = Field(
        default=None,
        max_length=1000,
    )
    score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )
    data: dict | None = Field(
        default=None,
    )

    @field_validator("data")
    @classmethod
    def validate_data_size(cls, v: dict | None) -> dict | None:
        if v is not None:
            try:
                serialized = json.dumps(v)
                if len(serialized) > 500000:
                    raise ValueError("Payload data exceeds maximum allowed size (500KB).")
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid JSON data payload: {e}")
        return v


class LearningActivityResponse(BaseModel):
    id: int
    user_id: int
    activity_type: str
    title: str
    summary: str | None
    score: float | None
    data: dict | None
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }
