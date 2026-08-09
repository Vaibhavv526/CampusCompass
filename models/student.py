from dataclasses import dataclass, field
from typing import List

from .skill import Skill


@dataclass
class StudentProfile:
    """Core profile representing a student's academic and career context."""

    name: str
    email: str
    degree: str
    branch: str
    current_year: int
    semester: int
    career_goal: str
    interests: List[str] = field(default_factory=list)
    weekly_hours: float = 0.0
    skills: List[Skill] = field(default_factory=list)

    def get_skill(self, skill_name: str) -> Skill | None:
        """Return a skill by name, or None if it is not present."""
        for skill in self.skills:
            if skill.name.lower() == skill_name.lower():
                return skill
        return None

    def get_skill_gap(self, skill_name: str) -> float:
        """Return the proficiency gap for a skill."""
        skill = self.get_skill(skill_name)
        return skill.gap if skill else 0.0