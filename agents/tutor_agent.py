from phi.agent import Agent
from phi.model.groq import Groq

from models.student import StudentProfile
from models.tutor_schema import TutorResponse


class TutorAgent:
    """Explains learning topics according to a student's level and goal."""

    def __init__(
        self,
        model_name: str = "openai/gpt-oss-20b",
    ):
        self.agent = Agent(
            model=Groq(id=model_name),
            system_prompt=(
                "You are a patient and practical AI tutor. "
                "Explain concepts according to the student's current "
                "knowledge level and career goal. "
                "Start from the student's existing understanding and "
                "gradually build toward the target concept. "
                "Use simple explanations, practical examples, and "
                "technical terminology when appropriate. "
                "Avoid unnecessary information. "
                "Return JSON with exactly these fields: "
                "topic, explanation, key_points, example, practice_task. "
                "key_points must be a list of strings. "
                "Do not create additional wrapper objects."
            ),
            structured_outputs=False,
        )

    def teach(
        self,
        student: StudentProfile,
        topic: str,
        question: str,
        roadmap_goal: str | None = None,
        skill_gaps: list[str] | None = None,
        recent_history: list[str] | None = None,
    ) -> TutorResponse:
        """Explain a topic and answer the student's question with contextual learning support."""

        context_lines = []
        if roadmap_goal:
            context_lines.append(f"- Active Roadmap Goal / Milestone: {roadmap_goal}")
        if skill_gaps:
            context_lines.append(f"- Identified Skill Gaps to Address: {', '.join(skill_gaps)}")
        if recent_history:
            context_lines.append(f"- Recent Learning History: {', '.join(recent_history)}")

        context_block = ""
        if context_lines:
            joined = "\n".join(context_lines)
            context_block = f"\nCURRENT LEARNING CONTEXT:\n{joined}\n"

        prompt = f"""
Teach the following topic to this student.

STUDENT:
- Name: {student.name}
- Degree: {student.degree}
- Branch: {student.branch}
- Current Year: {student.current_year}
- Semester: {student.semester}
- Career Goal: {student.career_goal}
{context_block}
QUESTION:
{question}

TOPIC:
{topic}

Explain the concept at an appropriate level for the student.

Requirements:
1. Directly answer the student's question.
2. Explain the underlying concept clearly.
3. Give a practical example.
4. Provide 3-5 key points.
5. Give one small practice task.
6. Keep the explanation focused on the requested topic.
7. Where relevant, connect the explanation to the student's active roadmap goal and address identified skill gaps.

Return only valid JSON.
"""

        response = self.agent.run(prompt)

        if response.content is None:
            raise RuntimeError(
                "Tutor agent returned an empty response."
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

        import json

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Tutor agent returned invalid JSON: {e}"
            ) from e

        return TutorResponse.model_validate(data)
