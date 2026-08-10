from phi.agent import Agent
from phi.model.groq import Groq
import json

from models.quiz_schema import QuizResponse
class QuizAgent:
    """Generates personalized quizzes for a student."""

    def __init__(
        self,
        model_name: str = "llama-3.1-8b-instant",
    ):  ##
        self.agent = Agent(
            model=Groq(
                id=model_name,
                temperature=0,
            ),
            output_schema=QuizResponse,
            
            system_prompt=(
                "You are a personalized quiz generation agent. "
                "Create quizzes based on the student's topic, "
                "knowledge level, and learning goal. "
                "Generate clear and educational multiple-choice questions. "
                "Each question must have exactly four options. "
                "The correct_answer must exactly match one of the options. "
                "Provide a concise explanation for every answer. "
                "Return ONLY one valid JSON object. "
                "Do not use markdown code fences. "
                "Do not write any text before or after the JSON. "
                "Do not use trailing commas. "
                "Use double quotes for all JSON keys and string values. "
                "The JSON must be directly parseable by Python json.loads(). "
                "Return JSON that matches the QuizResponse structure exactly. "
                "Do not add wrapper objects or extra fields. "
            ),
            structured_outputs=True,
        )
    ###
    def generate(
        self,
        topic: str,
        knowledge_level: str,
        learning_goal: str,
        num_questions: int = 5,
    ) -> QuizResponse:
        """Generate and validate a personalized quiz."""
        
        prompt = f"""
Create a quiz for the following student.

TOPIC:
{topic}

KNOWLEDGE LEVEL:
{knowledge_level}

LEARNING GOAL:
{learning_goal}

NUMBER OF QUESTIONS:
{num_questions}

Requirements:

1. Generate exactly {num_questions} questions.
2. Each question must have exactly four options.
3. Each correct_answer must exactly match one option.
4. Include a concise explanation for every answer.
5. Set an appropriate difficulty based on the student's knowledge level.
6. Questions should help the student progress toward their learning goal.

7. Return exactly this JSON structure:
   {{
   "topic": "...",
   "difficulty": "...",
   "questions": [
   {{
   "question": "...",
   "options": ["...", "...", "...", "..."],
   "correct_answer": "...",
   "explanation": "..."
   }}
   ]
   }}

8. The "questions" array MUST contain exactly
   {num_questions} question objects.

9. Never return an empty "questions" array.
10. Do not use a field named "results".
11. Do not omit the "questions" field.
"""
        response = self.agent.run(prompt)

        if response.content is None:
            raise RuntimeError(
                "Quiz agent returned an empty response."
            )

        # Structured output should already be parsed by Phi.
        if isinstance(response.content, QuizResponse):
            result = response.content

        elif isinstance(response.content, str):
            content = response.content.strip()

            # Remove markdown fences if the model adds them.
            if "```json" in content:
                content = content.split("```json", 1)[1]
                content = content.split("```", 1)[0].strip()
            elif "```" in content:
                content = content.split("```", 1)[1]
                content = content.split("```", 1)[0].strip()

            # Keep only the JSON object.
            start = content.find("{")
            end = content.rfind("}")

            if start == -1 or end == -1 or start >= end:
                raise RuntimeError(
                    "Quiz agent did not return a JSON object."
                )

            content = content[start:end + 1]
            ##
            try:
                data = json.loads(content)

            except json.JSONDecodeError as e:
                repair_prompt = f"""
            The following quiz response is intended to be JSON
            but contains invalid JSON syntax.

            Fix ONLY the JSON syntax.
            Do not change the quiz content.
            Do not add questions.
            Do not remove questions.
            Do not add explanations.
            Do not use markdown.
            Return ONLY one valid JSON object.

            INVALID JSON:
            {content}
            """

                repair_response = self.agent.run(repair_prompt)

                if repair_response.content is None:
                    raise RuntimeError(
                        f"Quiz agent returned invalid JSON: {e}"
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

                start = repaired.find("{")
                end = repaired.rfind("}")

                if start == -1 or end == -1 or start >= end:
                    raise RuntimeError(
                        f"Quiz agent returned invalid JSON: {e}"
                    ) from e

                repaired = repaired[start:end + 1]

                try:
                    data = json.loads(repaired)

                except json.JSONDecodeError as repair_error:
                    raise RuntimeError(
                        "Quiz agent returned invalid JSON "
                        f"after repair: {repair_error}"
                    ) from repair_error


            # Normalize common model variations into QuizResponse.
            if "topic" not in data:
                data["topic"] = topic

            if "difficulty" not in data:
                data["difficulty"] = knowledge_level

            if "questions" not in data and "results" in data:
                data["questions"] = data.pop("results")

            try:
                result = QuizResponse.model_validate(data)

            except Exception as e:
                raise RuntimeError(
                    f"Quiz response failed schema validation: {e}"
                ) from e

        else:
            try:
                result = QuizResponse.model_validate(
                    response.content
                )
            except Exception as e:
                raise RuntimeError(
                    f"Quiz response failed schema validation: {e}"
                ) from e

        # Validate the requested number of questions.
        if len(result.questions) == 0:
            raise RuntimeError(
                "Quiz agent returned an empty question list."
            )

        if len(result.questions) != num_questions:
            raise RuntimeError(
                f"Quiz agent returned {len(result.questions)} "
                f"questions; expected {num_questions}."
            )

        # Validate every question.
        for index, question in enumerate(
            result.questions,
            start=1,
        ):
            if len(question.options) != 4:
                raise RuntimeError(
                    f"Question {index} has "
                    f"{len(question.options)} options; expected 4."
                )

            if question.correct_answer not in question.options:
                repair_prompt = f"""
        The following quiz question has an invalid correct_answer.

        The correct_answer MUST exactly match one of the four options.

        Question:
        {question.question}

        Options:
        {json.dumps(question.options, indent=2)}

        Current correct_answer:
        {question.correct_answer}

        Fix ONLY the correct_answer.

        Return ONLY the exact text of one option.
        Do not return JSON.
        Do not return an explanation.
        Do not add punctuation.
        """

                repair_response = self.agent.run(repair_prompt)

                if repair_response.content is None:
                    raise RuntimeError(
                        f"Question {index} has an invalid correct_answer."
                    )

                repaired_answer = repair_response.content.strip()

                # Remove accidental markdown/code formatting.
                repaired_answer = repaired_answer.replace(
                    "```", ""
                ).strip()

                if repaired_answer not in question.options:
                    raise RuntimeError(
                        f"Question {index} has a correct_answer "
                        "that does not match any option, even after repair."
                    )

                question.correct_answer = repaired_answer

        return result