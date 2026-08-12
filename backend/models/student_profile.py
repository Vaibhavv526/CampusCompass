from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base

class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    degree: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    branch: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    current_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    semester: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    career_goal: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    interests: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    weekly_hours: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="student_profile",
    )
    skills: Mapped[list["StudentSkill"]] = relationship(
        "StudentSkill",
        back_populates="student_profile",
        cascade="all, delete-orphan",
    )