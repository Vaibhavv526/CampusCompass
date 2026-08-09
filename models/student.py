from dataclasses import dataclass, field
from typing import Dict, List


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
    skills: Dict[str, float] = field(default_factory=dict)