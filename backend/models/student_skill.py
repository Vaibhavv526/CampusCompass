from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

class StudentSkill(Base):
    __tablename__ = "student_skills"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    student_profile_id: Mapped[int] = mapped_column(
        ForeignKey(
            "student_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    proficiency: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    strengths: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    weak_areas: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    experience: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    student_profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile",
        back_populates="skills",
    )