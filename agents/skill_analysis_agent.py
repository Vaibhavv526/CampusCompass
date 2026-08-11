from phi.agent import Agent
from phi.model.groq import Groq
import json
from typing import Any

from models.skill_analysis_schema import SkillAnalysisResponse
from backend.schemas.skill_analysis import SkillInput

class SkillAnalysisAgent:
    """Analyzes user-provided skills and identifies strengths and gaps."""

    def __init__(
        self,
        model_name: str = "llama-3.1-8b-instant",
    ):
        self.agent = Agent(
            model=Groq(id=model_name),
            system_prompt=(
                "You are an AI skill analysis mentor. "
                "Analyze the technical skills and information provided by a student. "

                "The student provides their own proficiency score. "
                "Use that proficiency as the baseline and do not invent a different score. "

                "Use the student's provided strengths, weak areas, and experience "
                "as evidence when generating the analysis. "

                "Identify realistic skill gaps and actionable next steps. "
                "Be specific, realistic, and concise. "

                "Return ONLY valid JSON. "
                "Do not return markdown. "
                "Do not return explanations outside the JSON. "

                "The response MUST have exactly these top-level fields: "
                "summary and skills. "

                "Each object inside skills MUST have exactly these fields: "
                "name, proficiency, strengths, weak_areas, gap, next_steps. "

                "The fields strengths, weak_areas, and next_steps MUST always be arrays of strings. "
                "The field gap MUST always be a string. "
                "The field proficiency MUST always be a number from 0 to 100. "

                "Do not use alternative field names such as recommendations, "
                "recommendation, improvements, areas_to_improve, actions, or tasks. "

                "Do not omit strengths. "
                "Do not omit weak_areas. "
                "Do not omit next_steps. "

                "Analyze every skill provided by the student. "
                "Do not omit any skill."
            ),
            structured_outputs=False,
        )

    def analyze(self, skills: list[SkillInput]) -> SkillAnalysisResponse:
        """Analyze the provided skills and return a structured response."""

        skills_text = "\n".join(
                f"""
            Skill: {skill.name}
            Student Proficiency: {skill.proficiency}/100
            Strengths: {skill.strengths or "Not provided"}
            Weak Areas: {skill.weak_areas or "Not provided"}
            Projects / Experience: {skill.experience or "Not provided"}
            """.strip()
                for skill in skills
            )

        prompt = f"""
Analyze the following technical skills for a student:

Skills:
{skills_text}

For every skill, provide:

- name
- proficiency: number from 0 to 100
- strengths: list of specific strengths
- weak_areas: list of areas that need improvement
- gap: concise description of the current skill gap
- next_steps: practical steps the student should take

Also provide a concise overall summary.

Return ONLY valid JSON.

The JSON must contain exactly:
- summary: string
- skills: array

Each skill object must contain exactly:
- name: string
- proficiency: number from 0 to 100
- strengths: array of strings
- weak_areas: array of strings
- gap: string
- next_steps: array of strings
"""

        response = self.agent.run(prompt)

        if response.content is None:
            raise RuntimeError(
                "Skill analysis agent returned an empty response."
            )

        print("RAW SKILL ANALYSIS RESPONSE:")
        print(repr(response.content))

        try:
            content = response.content.strip()

            if "```json" in content:
                content = (
                    content.split("```json", 1)[1]
                    .split("```", 1)[0]
                    .strip()
                )

            elif "```" in content:
                content = (
                    content.split("```", 1)[1]
                    .split("```", 1)[0]
                    .strip()
                )

            data: dict[str, Any] = json.loads(content)

            return SkillAnalysisResponse.model_validate(data)

        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Skill analysis agent returned invalid JSON: {e}"
            ) from e