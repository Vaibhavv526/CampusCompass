import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database.session import SessionLocal
from backend.models.user import User
from backend.models.learning_activity import LearningActivity
from models.student import StudentProfile
from models.roadmap import LearningRoadmap, RoadmapStep
from models.tutor_schema import TutorResponse
from models.quiz_schema import QuizResponse, QuizQuestion
from models.quiz_evaluation_schema import QuizEvaluationResponse
from models.assessment_schema import (
    LearningAssessmentResponse,
    StudentAssessmentSummary,
    SkillGapResponse,
    LearningRecommendation,
)


class TestContextualCollaboration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()

        cls.user1_email = "student1_collab@campuscompass.org"
        cls.user2_email = "student2_collab@campuscompass.org"
        cls.password = "ValidPassword123!"

        cls._cleanup()

        # Register User 1
        res1 = cls.client.post(
            "/auth/register",
            json={
                "full_name": "Student One",
                "email": cls.user1_email,
                "password": cls.password,
            },
        )
        assert res1.status_code == 201, f"User 1 registration failed: {res1.text}"

        # Login User 1
        login1 = cls.client.post(
            "/auth/login",
            data={"username": cls.user1_email, "password": cls.password},
        )
        cls.user1_token = login1.json()["access_token"]
        cls.user1_headers = {"Authorization": f"Bearer {cls.user1_token}"}
        cls.user1 = cls.db.query(User).filter(User.email == cls.user1_email).first()

        # Register User 2
        res2 = cls.client.post(
            "/auth/register",
            json={
                "full_name": "Student Two",
                "email": cls.user2_email,
                "password": cls.password,
            },
        )
        assert res2.status_code == 201, f"User 2 registration failed: {res2.text}"

        # Login User 2
        login2 = cls.client.post(
            "/auth/login",
            data={"username": cls.user2_email, "password": cls.password},
        )
        cls.user2_token = login2.json()["access_token"]
        cls.user2_headers = {"Authorization": f"Bearer {cls.user2_token}"}
        cls.user2 = cls.db.query(User).filter(User.email == cls.user2_email).first()

        cls._populate_user1_history()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup()
        cls.db.close()

    @classmethod
    def _cleanup(cls):
        for email in [cls.user1_email, cls.user2_email]:
            user = cls.db.query(User).filter(User.email == email).first()
            if user:
                cls.db.query(LearningActivity).filter(LearningActivity.user_id == user.id).delete()
                cls.db.delete(user)
                cls.db.commit()

    @classmethod
    def _populate_user1_history(cls):
        # 1. Assessment Activity
        assessment_data = {
            "summary": {
                "student_name": "Student One",
                "degree": "B.Tech",
                "branch": "CS",
                "current_year": 3,
                "semester": 5,
                "career_goal": "AI Engineer",
                "weekly_study_hours": 15,
            },
            "skill_gaps": [
                {
                    "skill_name": "Deep Learning Fundamentals",
                    "current_level": 30,
                    "target_level": 80,
                    "gap": 50,
                    "priority": "High",
                    "task": "Study Backpropagation",
                    "resources": ["FastAI"],
                    "timeline": "3 weeks",
                },
                {
                    "skill_name": "PyTorch",
                    "current_level": 25,
                    "target_level": 75,
                    "gap": 50,
                    "priority": "High",
                    "task": "Build CNN models",
                    "resources": ["PyTorch Tutorials"],
                    "timeline": "4 weeks",
                },
            ],
            "recommendations": [
                {"description": "Focus on neural networks", "timeline": "Next 2 weeks"}
            ],
        }
        cls.db.add(
            LearningActivity(
                user_id=cls.user1.id,
                activity_type="assessment",
                title="Learning Assessment: AI Engineer",
                summary="Gaps in Deep Learning Fundamentals and PyTorch",
                score=None,
                data=assessment_data,
            )
        )

        # 2. Roadmap Activity
        roadmap_data = {
            "title": "AI Engineer Learning Roadmap",
            "target_role": "AI Engineer",
            "steps": [
                {
                    "title": "Master Deep Learning & PyTorch",
                    "description": "Understand core tensor operations and neural networks",
                    "skills": ["Deep Learning", "PyTorch"],
                    "estimated_hours": 20.0,
                    "completed": False,
                },
                {
                    "title": "Computer Vision Projects",
                    "description": "Build object detection models",
                    "skills": ["PyTorch", "OpenCV"],
                    "estimated_hours": 25.0,
                    "completed": False,
                },
            ],
        }
        cls.db.add(
            LearningActivity(
                user_id=cls.user1.id,
                activity_type="roadmap",
                title="AI Engineer Learning Roadmap",
                summary="0 of 2 steps completed (0%)",
                score=0.0,
                data=roadmap_data,
            )
        )

        # 3. Quiz Activity
        quiz_data = {
            "topic": "Neural Networks",
            "quiz": {"topic": "Neural Networks", "difficulty": "intermediate", "questions": []},
            "answers": ["A", "C"],
            "evaluation": {
                "topic": "Neural Networks",
                "total_questions": 5,
                "correct_answers": 3,
                "score_percentage": 60.0,
                "weak_topics": ["Backpropagation", "Gradient Descent"],
                "recommendation": "Review loss functions and backprop calculus.",
            },
        }
        cls.db.add(
            LearningActivity(
                user_id=cls.user1.id,
                activity_type="quiz",
                title="Quiz: Neural Networks",
                summary="Score: 3/5 (60%)",
                score=60.0,
                data=quiz_data,
            )
        )

        cls.db.commit()

    def _sample_student_payload(self):
        return {
            "name": "Attacker Name Spoof",
            "email": "attacker@spoofed.com",
            "degree": "B.Tech",
            "branch": "Computer Science",
            "current_year": 3,
            "semester": 5,
            "career_goal": "AI Engineer",
            "interests": ["Machine Learning", "Vision"],
            "weekly_hours": 12,
            "skills": [
                {
                    "name": "Python",
                    "category": "Technical Skill",
                    "current_level": 60,
                    "target_level": 85,
                }
            ],
        }

    # --- Test 1: Assessment -> Roadmap (Reuses existing assessment from history) ---

    @patch("orchestrator.RoadmapAgent.create")
    def test_roadmap_reuses_existing_assessment_from_history(self, mock_roadmap_create):
        mock_roadmap_create.return_value = LearningRoadmap(
            title="AI Engineer Learning Roadmap",
            target_role="AI Engineer",
            steps=[
                RoadmapStep(
                    title="Master Deep Learning",
                    description="Study deep learning",
                    skills=["PyTorch"],
                    estimated_hours=20,
                    completed=False,
                )
            ],
        )

        payload = {
            "student": self._sample_student_payload(),
            "assessment": None,
        }

        res = self.client.post("/api/roadmap", json=payload, headers=self.user1_headers)
        self.assertEqual(res.status_code, 200, f"Error: {res.text}")

        # Verify that mock_roadmap_create was called with the assessment loaded from history
        mock_roadmap_create.assert_called_once()
        _, kwargs = mock_roadmap_create.call_args
        assessment_arg = kwargs.get("assessment") or mock_roadmap_create.call_args[0][1]
        self.assertIsNotNone(assessment_arg)
        self.assertEqual(len(assessment_arg.skill_gaps), 2)
        self.assertEqual(assessment_arg.skill_gaps[0].skill_name, "Deep Learning Fundamentals")

    # --- Test 2: Roadmap Fallback when No Assessment in History ---

    @patch("orchestrator.RoadmapAgent.create")
    @patch("orchestrator.AssessmentAgent.assess")
    def test_roadmap_fallback_when_no_assessment_in_history(self, mock_assess, mock_roadmap_create):
        # User 2 has no assessment in history
        mock_assess.return_value = LearningAssessmentResponse(
            summary=StudentAssessmentSummary(
                student_name="Student Two",
                degree="B.Tech",
                branch="CS",
                current_year=2,
                semester=3,
                career_goal="Data Scientist",
                weekly_study_hours=10,
            ),
            skill_gaps=[
                SkillGapResponse(
                    skill_name="Statistics",
                    current_level=40,
                    target_level=80,
                    gap=40,
                    priority="High",
                    task="Study Probability",
                    timeline="2 weeks",
                )
            ],
            recommendations=[LearningRecommendation(description="Study Stats", timeline="2 weeks")],
        )

        mock_roadmap_create.return_value = LearningRoadmap(
            title="Data Science Roadmap",
            target_role="Data Scientist",
            steps=[],
        )

        payload = {
            "student": self._sample_student_payload(),
            "assessment": None,
        }

        res = self.client.post("/api/roadmap", json=payload, headers=self.user2_headers)
        self.assertEqual(res.status_code, 200, f"Error: {res.text}")

        # Verify that orchestrator fell back to assessing student
        mock_assess.assert_called_once()
        mock_roadmap_create.assert_called_once()

    # --- Test 3: Roadmap -> Contextual Tutor (Injects roadmap milestone & skill gaps from history) ---

    @patch("orchestrator.TutorAgent.teach")
    def test_tutor_incorporates_roadmap_goal_and_skill_gaps_from_history(self, mock_teach):
        mock_teach.return_value = TutorResponse(
            topic="PyTorch Tensors",
            explanation="Tensors are multi-dimensional arrays with GPU acceleration.",
            key_points=["Multi-dimensional", "GPU support", "Autograd compatible"],
            example="import torch; x = torch.tensor([1, 2, 3])",
            practice_task="Create a 3x3 random tensor and compute its transpose.",
        )

        payload = {
            "student": self._sample_student_payload(),
            "topic": "PyTorch Tensors",
            "question": "How do GPU tensors work?",
        }

        res = self.client.post("/api/tutor", json=payload, headers=self.user1_headers)
        self.assertEqual(res.status_code, 200, f"Error: {res.text}")

        mock_teach.assert_called_once()
        _, kwargs = mock_teach.call_args

        # Verify contextual learning data was resolved from user 1's history
        self.assertEqual(kwargs.get("roadmap_goal"), "Master Deep Learning & PyTorch")
        self.assertIn("Deep Learning Fundamentals", kwargs.get("skill_gaps", []))
        self.assertIn("PyTorch", kwargs.get("skill_gaps", []))
        self.assertTrue(len(kwargs.get("recent_history", [])) > 0)

    # --- Test 4: Authenticated Identity Binding across AI Endpoints ---

    @patch("orchestrator.TutorAgent.teach")
    def test_tutor_uses_authenticated_identity_not_client_override(self, mock_teach):
        mock_teach.return_value = TutorResponse(
            topic="Python",
            explanation="Explanation",
            key_points=["Point 1"],
            example="Example",
            practice_task="Task",
        )

        payload = {
            "student": self._sample_student_payload(),  # Contains "Attacker Name Spoof"
            "topic": "Python",
            "question": "What is a generator?",
        }

        res = self.client.post("/api/tutor", json=payload, headers=self.user1_headers)
        self.assertEqual(res.status_code, 200)

        # The student profile passed to teach MUST have the authenticated user's name
        student_arg = mock_teach.call_args[1].get("student") or mock_teach.call_args[0][0]
        self.assertEqual(student_arg.name, "Student One")
        self.assertEqual(student_arg.email, self.user1_email)

    # --- Test 5: Cross-User Data Isolation ---

    @patch("orchestrator.TutorAgent.teach")
    def test_cross_user_context_isolation(self, mock_teach):
        mock_teach.return_value = TutorResponse(
            topic="Python",
            explanation="Explanation",
            key_points=["Point 1"],
            example="Example",
            practice_task="Task",
        )

        # User 2 has NO history populated
        payload = {
            "student": self._sample_student_payload(),
            "topic": "Python",
            "question": "What is recursion?",
        }

        res = self.client.post("/api/tutor", json=payload, headers=self.user2_headers)
        self.assertEqual(res.status_code, 200)

        # User 2 should NOT see User 1's roadmap goal or skill gaps
        _, kwargs = mock_teach.call_args
        self.assertIsNone(kwargs.get("roadmap_goal"))
        self.assertFalse(kwargs.get("skill_gaps"))
        self.assertFalse(kwargs.get("recent_history"))

    # --- Test 6: Learning Context -> Adaptive Quiz (Uses weak areas & milestone from history) ---

    @patch("orchestrator.QuizAgent.generate")
    def test_adaptive_quiz_incorporates_weak_areas_and_milestone_from_history(self, mock_quiz_generate):
        mock_quiz_generate.return_value = QuizResponse(
            topic="Neural Networks",
            difficulty="intermediate",
            questions=[
                QuizQuestion(
                    question="What algorithm is used to compute gradients?",
                    options=["Backpropagation", "Heapsort", "Dijkstra", "K-Means"],
                    correct_answer="Backpropagation",
                    explanation="Backpropagation calculates gradient of the loss function.",
                )
            ]
            * 5,
        )

        payload = {
            "student": self._sample_student_payload(),
            "topic": "Neural Networks",
            "num_questions": 5,
        }

        res = self.client.post("/api/quiz", json=payload, headers=self.user1_headers)
        self.assertEqual(res.status_code, 200, f"Error: {res.text}")

        mock_quiz_generate.assert_called_once()
        _, kwargs = mock_quiz_generate.call_args

        # Weak areas from User 1's prior quiz: ["Backpropagation", "Gradient Descent"]
        self.assertIn("Backpropagation", kwargs.get("weak_areas", []))
        self.assertIn("Gradient Descent", kwargs.get("weak_areas", []))
        self.assertEqual(kwargs.get("roadmap_milestone"), "Master Deep Learning & PyTorch")

    # --- Test 7: Explicit Context Parameters Precedence ---

    @patch("orchestrator.QuizAgent.generate")
    def test_explicit_context_parameters_precedence(self, mock_quiz_generate):
        mock_quiz_generate.return_value = QuizResponse(
            topic="Algorithms",
            difficulty="intermediate",
            questions=[
                QuizQuestion(
                    question="What is time complexity of merge sort?",
                    options=["O(N log N)", "O(N^2)", "O(N)", "O(1)"],
                    correct_answer="O(N log N)",
                    explanation="Merge sort is O(N log N).",
                )
            ]
            * 5,
        )

        payload = {
            "student": self._sample_student_payload(),
            "topic": "Algorithms",
            "num_questions": 5,
            "weak_areas": ["Dynamic Programming"],
            "roadmap_milestone": "Custom Milestone",
        }

        res = self.client.post("/api/quiz", json=payload, headers=self.user1_headers)
        self.assertEqual(res.status_code, 200)

        mock_quiz_generate.assert_called_once()
        _, kwargs = mock_quiz_generate.call_args
        self.assertEqual(kwargs.get("weak_areas"), ["Dynamic Programming"])
        self.assertEqual(kwargs.get("roadmap_milestone"), "Custom Milestone")

    # --- Test 8: Quiz Evaluation Uses Submitted Quiz and Answers ---

    @patch("backend.routes.quiz.QuizEvaluationAgent.evaluate")
    def test_quiz_evaluation_receives_submitted_quiz_and_answers(self, mock_evaluate):
        mock_evaluate.return_value = QuizEvaluationResponse(
            topic="Neural Networks",
            total_questions=1,
            correct_answers=1,
            score_percentage=100.0,
            question_results=[],
            weak_topics=[],
            recommendation="Great job!",
        )

        quiz_payload = {
            "quiz": {
                "topic": "Neural Networks",
                "difficulty": "intermediate",
                "questions": [
                    {
                        "question": "What is an epoch?",
                        "options": ["One pass over data", "A learning rate", "An optimizer", "A neuron"],
                        "correct_answer": "One pass over data",
                        "explanation": "An epoch is one full pass over the training dataset.",
                    }
                ],
            },
            "student_answers": ["One pass over data"],
        }

        res = self.client.post("/api/quiz/evaluate", json=quiz_payload, headers=self.user1_headers)
        self.assertEqual(res.status_code, 200, f"Error: {res.text}")

        mock_evaluate.assert_called_once()
        call_quiz = mock_evaluate.call_args[1].get("quiz") or mock_evaluate.call_args[0][0]
        call_answers = mock_evaluate.call_args[1].get("student_answers") or mock_evaluate.call_args[0][1]

        self.assertEqual(call_quiz.topic, "Neural Networks")
        self.assertEqual(call_answers, ["One pass over data"])

    # --- Test 9: Backward Compatibility of Existing Endpoints ---

    @patch("orchestrator.RoadmapAgent.create")
    def test_roadmap_endpoint_backward_compatibility_with_explicit_assessment(self, mock_roadmap_create):
        mock_roadmap_create.return_value = LearningRoadmap(
            title="Roadmap",
            target_role="AI Engineer",
            steps=[],
        )

        assessment_payload = {
            "summary": {
                "student_name": "Student One",
                "degree": "B.Tech",
                "branch": "CS",
                "current_year": 3,
                "semester": 5,
                "career_goal": "AI Engineer",
                "weekly_study_hours": 15,
            },
            "skill_gaps": [],
            "recommendations": [],
        }

        payload = {
            "student": self._sample_student_payload(),
            "assessment": assessment_payload,
        }

        res = self.client.post("/api/roadmap", json=payload, headers=self.user1_headers)
        self.assertEqual(res.status_code, 200)

    # --- Test 10: Authentication Protection Enforced ---

    def test_unauthenticated_requests_rejected(self):
        payload = {"student": self._sample_student_payload(), "topic": "Python", "question": "Explain lists"}
        res = self.client.post("/api/tutor", json=payload)
        self.assertEqual(res.status_code, 401)

        res_quiz = self.client.post("/api/quiz", json=payload)
        self.assertEqual(res_quiz.status_code, 401)

        res_roadmap = self.client.post("/api/roadmap", json=payload)
        self.assertEqual(res_roadmap.status_code, 401)


if __name__ == "__main__":
    unittest.main()
