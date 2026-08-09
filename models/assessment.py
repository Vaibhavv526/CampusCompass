from dataclasses import dataclass, field
from typing import List


@dataclass
class SkillGap:
    """Represents a gap identified in a specific skill."""

    skill_name: str
    current_level: float
    target_level: float
    priority: str = "medium"

    @property
    def gap(self) -> float:
        """Return the remaining proficiency gap."""
        return max(0.0, self.target_level - self.current_level)


@dataclass
class LearningAssessment:
    """Represents the overall result of a student's learning assessment."""

    summary: str
    skill_gaps: List[SkillGap] = field(default_factory=list)
    recommended_focus: List[str] = field(default_factory=list)

    def get_high_priority_gaps(self) -> List[SkillGap]:
        """Return skill gaps marked as high priority."""
        return [
            gap for gap in self.skill_gaps
            if gap.priority.lower() == "high"
        ]