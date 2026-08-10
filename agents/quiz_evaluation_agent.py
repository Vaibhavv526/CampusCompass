from phi.agent import Agent
from phi.model.groq import Groq
import json

from models.quiz_evaluation_schema import QuizEvaluationResponse
from models.quiz_schema import QuizResponse


class QuizEvaluationAgent:
    """Evaluates a student's completed quiz."""

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
                "You are a quiz evaluation agent. "
                "Evaluate a student's answers against the provided quiz. "
                "Determine whether each answer is correct. "
                "Calculate the total score and percentage accurately. "
                "Identify weak topics based on incorrect answers. "
                "Provide a concise recommendation for improvement. "
                "Return ONLY one valid JSON object. "
                "Do not use markdown code fences. "
                "Do not add text before or after the JSON. "
                "Use double quotes for JSON keys and string values. "
                "The JSON must be directly parseable by Python json.loads(). "
                "Return JSON matching the QuizEvaluationResponse structure exactly."
            ),
            structured_outputs=False,
        )

    def evaluate(
        self,
        quiz: QuizResponse,
        student_answers: list[str],
    ) -> QuizEvaluationResponse:
        """Evaluate submitted answers against a quiz."""

        if len(student_answers) != len(quiz.questions):
            raise ValueError(
                f"Expected {len(quiz.questions)} answers, "
                f"but received {len(student_answers)}."
            )

        quiz_data = quiz.model_dump()

        prompt = f"""
Evaluate this completed quiz.

QUIZ:
{json.dumps(quiz_data, indent=2)}

STUDENT ANSWERS:
{json.dumps(student_answers, indent=2)}

Evaluation requirements:

1. Evaluate every question.
2. Preserve the original question text.
3. Preserve the original correct answer.
4. Record the student's submitted answer.
5. Set is_correct=true only when the student's answer exactly
   matches the correct answer.
6. Calculate correct_answers accurately.
7. Calculate score_percentage as:

   correct_answers / total_questions * 100

8. Identify weak topics based on incorrect answers.
9. If all answers are correct, weak_topics should be an empty list.
10. Provide one concise recommendation.
11. Return exactly one QuizEvaluationResponse JSON object.

Return only valid JSON.
"""

        response = self.agent.run(prompt)

        if response.content is None:
            raise RuntimeError(
                "Quiz evaluation agent returned an empty response."
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
                "Quiz evaluation agent did not return valid JSON."
            )

        content = content[start:end + 1]

        try:
            data = json.loads(content)

        except json.JSONDecodeError as e:
            repair_prompt = f"""
        The following quiz evaluation response is intended to be JSON
        but contains invalid JSON syntax.

        Fix ONLY the JSON syntax.
        Do not change the evaluation content.
        Do not add explanations.
        Do not use markdown.
        Return ONLY one valid JSON object.

        INVALID JSON:
        {content}
        """

            repair_response = self.agent.run(repair_prompt)

            if repair_response.content is None:
                raise RuntimeError(
                    f"Quiz evaluation agent returned invalid JSON: {e}"
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
                    f"Quiz evaluation agent returned invalid JSON: {e}"
                ) from e

            repaired = repaired[start:end + 1]

            try:
                data = json.loads(repaired)

            except json.JSONDecodeError as repair_error:
                raise RuntimeError(
                    "Quiz evaluation agent returned invalid JSON "
                    f"after repair: {repair_error}"
                ) from repair_error
        # Normalize wrapped model responses.
        if "quiz_evaluation" in data:
            data = data["quiz_evaluation"]

        # Normalize deterministic fields using the original quiz.
        # These values must not depend on the LLM.
        data["topic"] = quiz.topic
        data["total_questions"] = len(quiz.questions)

        if "correct_answers" not in data:
            data["correct_answers"] = sum(
                1
                for question, student_answer in zip(
                    quiz.questions,
                    student_answers,
                )
                if student_answer.strip()
                == question.correct_answer.strip()
            )

        if "score_percentage" not in data:
            data["score_percentage"] = (
                data["correct_answers"]
                / data["total_questions"]
                * 100
                if data["total_questions"] > 0
                else 0.0
            )

        try:
            result = QuizEvaluationResponse.model_validate(data)
        except Exception as e:
            raise RuntimeError(
                f"Quiz evaluation failed schema validation: {e}"
            ) from e

        # Application-level validation.
        if result.total_questions != len(quiz.questions):
            raise RuntimeError(
                "Evaluation total_questions does not match the quiz."
            )

        if result.correct_answers < 0:
            raise RuntimeError(
                "Evaluation returned a negative correct answer count."
            )

        if result.correct_answers > result.total_questions:
            raise RuntimeError(
                "Evaluation returned more correct answers "
                "than total questions."
            )

        expected_percentage = (
            result.correct_answers
            / result.total_questions
            * 100
            if result.total_questions > 0
            else 0
        )

        if abs(
            result.score_percentage - expected_percentage
        ) > 0.01:
            raise RuntimeError(
                "Evaluation score percentage is inconsistent "
                "with the number of correct answers."
            )
        ##
        # Build authoritative question-level results in Python.
        # The LLM should not be trusted for answer matching.
        question_results = []

        for question, student_answer in zip(
            quiz.questions,
            student_answers,
        ):
            is_correct = (
                student_answer.strip()
                == question.correct_answer.strip()
            )

            question_results.append(
                {
                    "question": question.question,
                    "student_answer": student_answer,
                    "correct_answer": question.correct_answer,
                    "is_correct": is_correct,
                    "explanation": question.explanation,
                }
            )

        correct_answers = sum(
            result["is_correct"]
            for result in question_results
        )

        total_questions = len(quiz.questions)

        score_percentage = (
            correct_answers / total_questions * 100
            if total_questions > 0
            else 0.0
        )

        #
        # Derive weak topics from actual incorrect answers.
        # Never trust the LLM to report a weakness when all answers
        # were answered correctly.
        if correct_answers == total_questions:
            weak_topics = []
        else:
            weak_topics = result.weak_topics

        return QuizEvaluationResponse(
            topic=quiz.topic,
            total_questions=total_questions,
            correct_answers=correct_answers,
            score_percentage=score_percentage,
            question_results=question_results,
            weak_topics=weak_topics,
            recommendation=result.recommendation,
        )