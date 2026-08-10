from phi.agent import Agent
from phi.model.groq import Groq
import json

from models.roadmap import LearningRoadmap, RoadmapStep
from models.student import StudentProfile
from models.assessment_schema import LearningAssessmentResponse


class RoadmapAgent:
    """Creates a personalized learning roadmap from a student assessment."""

    def __init__(
        self,
        model_name: str = "llama-3.1-8b-instant",
    ):
        self.agent = Agent(
            model=Groq(id=model_name),
            system_prompt=(
                "You are a personalized learning roadmap agent. "
                "Create a practical, ordered learning roadmap for a student "
                "based on their career goal, skill gaps, and available study time. "
                "Prioritize high-impact skill gaps first. "
                "Break the roadmap into actionable learning steps. "
                "Each step must include a title, description, skills, "
                "estimated_hours, and completed status. "
                "The completed status must always be false for a new roadmap. "
                "Return ONLY a JSON object with exactly one top-level key: roadmap. "
                "The roadmap key must contain a list of actionable learning steps. "
                "Do NOT return summary, skill_gaps, recommendations, or any assessment data. "
                "Each roadmap step must contain exactly these fields: "
                "title, description, skills, estimated_hours, completed. "
                "skills must be a JSON array of strings. "
                "estimated_hours must be a number. "
                "completed must always be false."
            ),
            structured_outputs=False,
        )
    ##
    @staticmethod
    def _normalize_response(
        data: dict,
        student: StudentProfile,
    ) -> LearningRoadmap:
        """Normalize flexible LLM JSON into our roadmap model."""

        roadmap_items = data.get("roadmap", [])

        if not isinstance(roadmap_items, list):
            roadmap_items = []

        steps = []

        for item in roadmap_items:
            skills = item.get("skills", [])

            if isinstance(skills, str):
                skills = [
                    skill.strip()
                    for skill in skills.split(",")
                    if skill.strip()
                ]
            elif skills is None:
                skills = []

            steps.append(
                {
                    "title": str(item.get("title", "")),
                    "description": str(item.get("description", "")),
                    "skills": skills,
                    "estimated_hours": float(
                        item.get("estimated_hours", 0)
                    ),
                    "completed": bool(
                        item.get("completed", False)
                    ),
                }
            )
        
        max_hours = student.weekly_hours * 12
        total_hours = sum(
            step["estimated_hours"]
            for step in steps
        )

        if total_hours > max_hours and total_hours > 0:
            scale = max_hours / total_hours

            for step in steps:
                step["estimated_hours"] = round(
                    step["estimated_hours"] * scale,
                    2
                )

        return LearningRoadmap(
            title=f"{student.career_goal} Learning Roadmap",
            target_role=student.career_goal,
            steps=[
                RoadmapStep(**step)
                for step in steps
            ],
        )

    def create(
        self,
        student: StudentProfile,
        assessment: LearningAssessmentResponse,
    ) -> LearningRoadmap:
        """Create a personalized learning roadmap."""

        skill_gaps_text = "\n".join(
            f"- {gap.skill_name}: "
            f"current={gap.current_level}, "
            f"target={gap.target_level}, "
            f"gap={gap.gap}, "
            f"priority={gap.priority}, "
            f"task={gap.task}, "
            f"timeline={gap.timeline}"
            for gap in assessment.skill_gaps
        )

        prompt = f"""
Create a personalized learning roadmap for this student.

STUDENT:
- Name: {student.name}
- Degree: {student.degree}
- Branch: {student.branch}
- Current Year: {student.current_year}
- Semester: {student.semester}
- Career Goal: {student.career_goal}
- Weekly Study Hours: {student.weekly_hours}

SKILL GAPS:
{skill_gaps_text}

Create an ordered roadmap that:

1. Create exactly 6 to 8 learning steps.
2. Prioritize skills according to their priority:
   High first, then Medium, then Low.
3. Address all important skill gaps, but do not create repetitive steps.
4. Each step must represent a genuinely different learning activity.
5. Progress from fundamentals → practice → projects → AI/ML application.
6. Combine related activities instead of creating multiple similar steps.
7. Do not create steps such as "review progress", "adjust roadmap",
   "achieve target score", or other meta-management activities.
8. Do not repeat the same skill in multiple nearly identical steps.
9. Keep the roadmap realistic for a student with
   {student.weekly_hours} hours available per week.
10. estimated_hours represents the total estimated effort for that step.
11. This roadmap covers the next 12 weeks.
12. The total estimated_hours across all steps must not exceed
    {student.weekly_hours * 12} hours.
13. Prefer approximately 6 to 8 steps with a realistic distribution
    of the available study hours.
14. Do not create a step requiring more than 30 hours.
15. Every step must have completed=false.
16. Return exactly one top-level object:
    {{"roadmap": [...]}}
17. Do not return summary, skill_gaps, recommendations, rationale,
    explanation, or any other fields.
18. The roadmap must contain only actionable learning steps.

Return ONLY valid JSON.
"""

        response = self.agent.run(prompt)

        if response.content is None:
            raise RuntimeError(
                "Roadmap agent returned an empty response."
            )

        try:
            content = response.content.strip()

            if "```json" in content:
                content = content.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in content:
                content = content.split("```", 1)[1].split("```", 1)[0].strip()

            data = json.loads(content)

            return self._normalize_response(data, student)

        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Roadmap agent returned invalid JSON: {e}"
            ) from e
