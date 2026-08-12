from phi.agent import Agent
from phi.model.groq import Groq
import json

from models.recommendation_schema import RecommendationResponse
from models.student import StudentProfile


class RecommendationAgent:
    """Generates personalized recommendations for a student."""

    def __init__(
        self,
        model_name: str = "llama-3.1-8b-instant",
    ):
        self.agent = Agent(
            model=Groq(
                id=model_name,
                temperature=0,
            ),
            system_prompt=(
                "You are a personalized student recommendation agent. "
                "Analyze the student's profile, skills, career goal, "
                "and available study time. "
                "Recommend skills, projects, resources, and actionable "
                "next steps that align with the student's career goal. "
                "Recommendations must be realistic for the student's "
                "current skill level and available weekly study hours. "
                "Avoid generic recommendations when possible. "
                "Return ONLY one valid JSON object. "
                "Do not use markdown code fences. "
                "Do not add text before or after the JSON. "
                "Use double quotes for JSON keys and string values. "
                "Return JSON matching the RecommendationResponse "
                "structure exactly."
            ),
            structured_outputs=False,
        )

    def recommend(
        self,
        student: StudentProfile,
    ) -> RecommendationResponse:
        """Generate personalized recommendations."""

        student_data = {
            "name": student.name,
            "degree": student.degree,
            "branch": student.branch,
            "current_year": student.current_year,
            "semester": student.semester,
            "career_goal": student.career_goal,
            "interests": student.interests,
            "weekly_hours": student.weekly_hours,
            "skills": [
                {
                    "name": skill.name,
                    "category": skill.category,
                    "current_level": skill.current_level,
                    "target_level": skill.target_level,
                    "gap": skill.gap,
                }
                for skill in student.skills
            ],
        }

        prompt = f"""
Create personalized recommendations for this student.

STUDENT PROFILE:
{json.dumps(student_data, indent=2)}

Requirements:

1. Analyze the student's current skills.
2. Consider the student's career goal.
3. Consider the student's current academic year and semester.
4. Consider the student's weekly study hours.
5. Recommend skills that will help achieve the career goal.
6. Recommend practical projects appropriate for the student's level.
7. Recommend useful learning resources.
8. Provide clear and actionable next steps.
9. Keep recommendations realistic and prioritized.
10. Return exactly this JSON structure:

{{
    "summary": "...",
    "recommended_skills": ["...", "..."],
    "recommended_projects": ["...", "..."],
    "recommended_resources": ["...", "..."],
    "next_steps": ["...", "..."]
}}

Return ONLY valid JSON.
"""

        response = self.agent.run(prompt)

        if response.content is None:
            raise RuntimeError(
                "Recommendation agent returned an empty response."
            )

        content = response.content.strip()

        if "```json" in content:
            content = content.split(
                "```json", 1
            )[1].split("```", 1)[0].strip()

        elif "```" in content:
            content = content.split(
                "```", 1
            )[1].split("```", 1)[0].strip()

        start = content.find("{")
        end = content.rfind("}")

        if start == -1 or end == -1 or start >= end:
            raise RuntimeError(
                "Recommendation agent did not return valid JSON."
            )

        content = content[start:end + 1]

        try:
            data = json.loads(content)
            print(json.dumps(data, indent=2))
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Recommendation agent returned invalid JSON: {e}"
            ) from e
        # Normalize recommendation resources.
        # The LLM may return either strings or resource objects.

        normalized_resources = []

        for resource in data.get("recommended_resources", []):
            if isinstance(resource, str):
                normalized_resources.append(
                    {
                        "title": resource,
                        "link": "",
                        "type": "resource",
                    }
                )

            elif isinstance(resource, dict):
                normalized_resources.append(
                    {
                        "title": str(
                            resource.get("title")
                            or resource.get("name")
                            or "Recommended Resource"
                        ),
                        "link": str(
                            resource.get("link")
                            or resource.get("url")
                            or ""
                        ),
                        "type": str(
                            resource.get("type")
                            or "resource"
                        ),
                    }
                )

        data["recommended_resources"] = normalized_resources
        try:
            result = RecommendationResponse.model_validate(data)
        except Exception as e:
            raise RuntimeError(
                f"Recommendation response failed schema validation: {e}"
            ) from e

        return result