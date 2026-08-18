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
        model_name: str = "openai/gpt-oss-20b",
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
        ###
        summary = data.get("summary", {})

        if isinstance(summary, str) or not isinstance(summary, dict):
            summary = {}

        summary = {
            "student_name": summary.get("student_name", summary.get("name", student.name)),
            "degree": summary.get("degree", student.degree),
            "branch": summary.get("branch", student.branch),
            "current_year": summary.get("current_year", student.current_year),
            "semester": summary.get("semester", student.semester),
            "career_goal": summary.get("career_goal", student.career_goal),
            "weekly_study_hours": summary.get(
                "weekly_study_hours",
                student.weekly_hours,
            ),
        }
        
        normalized_gaps = []

        llm_gaps = {
            item.get("skill_name", "").strip().lower(): item
            for item in data.get("skill_gaps", [])
            if item.get("skill_name")
        }

        for skill in student.skills:
            item = llm_gaps.get(skill.name.strip().lower(), {})
            ##
            priority = item.get("priority")

            if priority is None:
                if skill.gap >= 40:
                    priority = "high"
                elif skill.gap >= 25:
                    priority = "medium"
                else:
                    priority = "low"

            elif isinstance(priority, int):
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
        ###
        for item in recommendations:

            if isinstance(item, str):
                normalized_recommendations.append({
                    "description": item,
                    "timeline": "",
                })
                continue

            if isinstance(item, dict):
                description = item.get(
                    "description",
                    item.get("task", "")
                )

                if not description:
                    description = item.get("title", "")

                timeline = item.get("timeline", "")

                if timeline is not None:
                    timeline = str(timeline)

                normalized_recommendations.append({
                    "description": str(description),
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
        print("RAW LLM RESPONSE:")
        print(repr(response.content))
        
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
            repair_prompt = f"""
    The following assessment response is intended to be JSON
    but contains invalid JSON syntax.

    Fix ONLY the JSON syntax.
    Do not change the meaning or evaluation content.
    Do not add explanations.
    Do not use markdown.
    Return ONLY one valid JSON object.

    INVALID JSON:
    {content}
    """

            repair_response = self.agent.run(repair_prompt)

            if repair_response.content is None:
                raise RuntimeError(
                    f"Assessment agent returned invalid JSON: {e}"
                ) from e

            repaired = repair_response.content.strip()

            if "```json" in repaired:
                repaired = repaired.split(
                    "```json", 1
                )[1].split("```", 1)[0].strip()

            elif "```" in repaired:
                repaired = repaired.split(
                    "```", 1
                )[1].split("```", 1)[0].strip()

            try:
                data = json.loads(repaired)

            except json.JSONDecodeError as repair_error:
                raise RuntimeError(
                    "Assessment agent returned invalid JSON "
                    f"after repair: {repair_error}"
                ) from repair_error

            normalized_data = self._normalize_response(
                data,
                student,
            )

            return LearningAssessmentResponse.model_validate(
                normalized_data
            )