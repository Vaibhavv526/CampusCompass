from dataclasses import dataclass


@dataclass
class Skill:
    """Represents a skill and the student's proficiency in that skill."""

    name: str
    category: str
    current_level: float = 0.0
    target_level: float = 100.0

    @property
    def gap(self) -> float:
        """Return the remaining proficiency gap."""
        return max(0.0, self.target_level - self.current_level)