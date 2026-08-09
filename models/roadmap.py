from dataclasses import dataclass, field
from typing import List


@dataclass
class RoadmapStep:
    """Represents one actionable step in a student's learning roadmap."""

    title: str
    description: str
    skills: List[str] = field(default_factory=list)
    estimated_hours: float = 0.0
    completed: bool = False


@dataclass
class LearningRoadmap:
    """Represents a personalized learning roadmap."""

    title: str
    target_role: str
    steps: List[RoadmapStep] = field(default_factory=list)