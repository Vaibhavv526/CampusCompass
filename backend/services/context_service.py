"""Service for retrieving student learning context across stages."""

from __future__ import annotations

import logging
from sqlalchemy.orm import Session

from backend.models.learning_activity import LearningActivity
from models.assessment_schema import LearningAssessmentResponse

logger = logging.getLogger(__name__)


def get_latest_assessment_activity(db: Session, user_id: int) -> LearningAssessmentResponse | None:
    """Retrieve the student's most recent valid assessment from learning history."""
    try:
        activity = (
            db.query(LearningActivity)
            .filter(
                LearningActivity.user_id == user_id,
                LearningActivity.activity_type == "assessment",
            )
            .order_by(LearningActivity.created_at.desc())
            .first()
        )
        if not activity or not activity.data:
            return None

        return LearningAssessmentResponse.model_validate(activity.data)
    except Exception as exc:
        logger.warning("Failed to parse cached assessment for user %s: %s", user_id, exc)
        return None


def get_tutor_context(
    db: Session,
    user_id: int,
) -> dict[str, any]:
    """Retrieve learning context for AI Tutor from roadmap and recent history."""
    context = {
        "roadmap_goal": None,
        "skill_gaps": [],
        "recent_history": [],
    }
    try:
        # 1. Latest roadmap milestone
        latest_roadmap = (
            db.query(LearningActivity)
            .filter(
                LearningActivity.user_id == user_id,
                LearningActivity.activity_type == "roadmap",
            )
            .order_by(LearningActivity.created_at.desc())
            .first()
        )
        if latest_roadmap and latest_roadmap.data:
            steps = latest_roadmap.data.get("steps", [])
            for step in steps:
                if isinstance(step, dict) and not step.get("completed", False):
                    context["roadmap_goal"] = step.get("title") or step.get("description")
                    break
            if not context["roadmap_goal"] and latest_roadmap.title:
                context["roadmap_goal"] = latest_roadmap.title

        # 2. Latest assessment skill gaps
        latest_assessment = (
            db.query(LearningActivity)
            .filter(
                LearningActivity.user_id == user_id,
                LearningActivity.activity_type == "assessment",
            )
            .order_by(LearningActivity.created_at.desc())
            .first()
        )
        if latest_assessment and latest_assessment.data:
            gaps = latest_assessment.data.get("skill_gaps", [])
            skill_names = []
            for gap in gaps:
                if isinstance(gap, dict) and gap.get("skill_name"):
                    skill_names.append(gap["skill_name"])
            if skill_names:
                context["skill_gaps"] = skill_names[:5]

        # 3. Recent learning history summaries
        recent_activities = (
            db.query(LearningActivity)
            .filter(LearningActivity.user_id == user_id)
            .order_by(LearningActivity.created_at.desc())
            .limit(3)
            .all()
        )
        summaries = []
        for act in recent_activities:
            desc = act.title
            if act.summary:
                desc += f" ({act.summary})"
            summaries.append(desc)
        context["recent_history"] = summaries
    except Exception as exc:
        logger.warning("Error fetching tutor context for user %s: %s", user_id, exc)

    return context


def get_quiz_context(
    db: Session,
    user_id: int,
) -> dict[str, any]:
    """Retrieve adaptive quiz context (weak areas and roadmap milestone)."""
    context = {
        "weak_areas": [],
        "roadmap_milestone": None,
    }
    try:
        # 1. Weak topics from latest quiz evaluation
        latest_quiz = (
            db.query(LearningActivity)
            .filter(
                LearningActivity.user_id == user_id,
                LearningActivity.activity_type == "quiz",
            )
            .order_by(LearningActivity.created_at.desc())
            .first()
        )
        if latest_quiz and latest_quiz.data:
            eval_data = latest_quiz.data.get("evaluation", {})
            weak_topics = eval_data.get("weak_topics", [])
            if isinstance(weak_topics, list):
                context["weak_areas"] = [str(t) for t in weak_topics if t][:5]

        # 2. Roadmap milestone from latest roadmap
        latest_roadmap = (
            db.query(LearningActivity)
            .filter(
                LearningActivity.user_id == user_id,
                LearningActivity.activity_type == "roadmap",
            )
            .order_by(LearningActivity.created_at.desc())
            .first()
        )
        if latest_roadmap and latest_roadmap.data:
            steps = latest_roadmap.data.get("steps", [])
            for step in steps:
                if isinstance(step, dict) and not step.get("completed", False):
                    context["roadmap_milestone"] = step.get("title")
                    break
    except Exception as exc:
        logger.warning("Error fetching quiz context for user %s: %s", user_id, exc)

    return context
