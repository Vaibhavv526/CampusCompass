from phi.agent import Agent
from phi.model.groq import Groq
import json
from typing import Any

from models.assessment_schema import LearningAssessmentResponse
from models.student import StudentProfile

class AssessmentAgent:
    """Analyzes a student profile and produces a structured learning assessment."""

    def __init__(
        self,
        model_name: str = "llama-3.1-8b-instant",
    ):
        self.agent = Agent(
            model=Groq(id=model_name),
            system_prompt=(
                "You are an academic assessment agent. "
                "Analyze a student's current skills, target levels, "
                "and career goal. Identify skill gaps and prioritize "
                "what the student should focus on next. "
                "Be specific, realistic, and concise. "
                "Return JSON that exactly matches the provided output schema. "
                "Use these field names exactly: "
                "summary, skill_gaps, recommendations, "
                "skill_name, current_level, target_level, gap, priority, "
                "task, resources, timeline. "
                "Do not create additional wrapper objects such as "
                "studentAssessment. "
                "Evaluate every skill provided in the student's profile. "
                "Do not omit a skill, even if its gap is small. "
                "For every skill, include current_level, target_level, gap, "
                "and priority. "
                "Provide at least one recommendation for the assessment. "
                "Recommendations should directly address the identified skill gaps."
            ),
            structured_outputs=False,
        )

    @staticmethod
    def _normalize_response(
    data: dict[str, Any],
    student: StudentProfile,
) -> dict[str, Any]:
        """Normalize flexible LLM JSON into our application schema."""

        summary = data.get("summary", {})

        if isinstance(summary, str):
            summary = {
                "student_name": student.name,
                "degree": student.degree,
                "branch": student.branch,
                "current_year": student.current_year,
                "semester": student.semester,
                "career_goal": student.career_goal,
                "weekly_study_hours": student.weekly_hours,
            }
        
        normalized_gaps = []

        llm_gaps = {
            item.get("skill_name", "").strip().lower(): item
            for item in data.get("skill_gaps", [])
            if item.get("skill_name")
        }

        for skill in student.skills:
            item = llm_gaps.get(skill.name.strip().lower(), {})

            priority = item.get("priority", "medium")

            if isinstance(priority, int):
                priority = {
                    1: "high",
                    2: "medium",
                    3: "low",
                }.get(priority, "medium")

            priority = str(priority).lower()

            task = item.get("task", "")

            if isinstance(task, list):
                task = " ".join(task)

            resources = item.get("resources", [])

            if isinstance(resources, str):
                resources = [resources]
            elif resources is None:
                resources = []

            timeline = item.get("timeline", "")

            if timeline is not None:
                timeline = str(timeline)

            normalized_gaps.append({
                "skill_name": skill.name,
                "current_level": skill.current_level,
                "target_level": skill.target_level,
                "gap": skill.gap,
                "priority": priority,
                "task": task,
                "resources": resources,
                "timeline": timeline,
            })
        
        normalized_recommendations = []

        recommendations = data.get("recommendations", [])

        if isinstance(recommendations, dict):
            recommendations = [recommendations]

        for item in recommendations:
            
            timeline = item.get("timeline", "")

            if timeline is not None:
                timeline = str(timeline)

            normalized_recommendations.append({
                "description": item.get(
                    "description",
                    item.get("task", "")
                ),
                "timeline": timeline,
            })

        return {
            "summary": summary,
            "skill_gaps": normalized_gaps,
            "recommendations": normalized_recommendations,
        }

    def assess(self, student: StudentProfile) -> LearningAssessmentResponse:
        """Analyze a student profile and return a structured assessment."""

        skills_text = "\n".join(
            f"- {skill.name}: current={skill.current_level}, "
            f"target={skill.target_level}, gap={skill.gap}"
            for skill in student.skills
        )

        prompt = f"""
Assess the following student.

Student:

- Name: {student.name}
- Degree: {student.degree}
- Branch: {student.branch}
- Current Year: {student.current_year}
- Semester: {student.semester}
- Career Goal: {student.career_goal}
- Weekly Study Hours: {student.weekly_hours}

Skills:
{skills_text}

Identify the most important skill gaps for this student's career goal.
Return the assessment using the required structured output schema.
"""

        response = self.agent.run(prompt)

        if response.content is None:
            raise RuntimeError("Assessment agent returned an empty response.")
        print("RAW:", repr(response.content))
        
        try:
            content = response.content.strip()

            if "```json" in content:
                content = content.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in content:
                content = content.split("```", 1)[1].split("```", 1)[0].strip()

            data = json.loads(content)

            normalized_data = self._normalize_response(data, student)

            return LearningAssessmentResponse.model_validate(normalized_data)

        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Assessment agent returned invalid JSON: {e}"
            ) from e