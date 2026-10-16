"""Service for computing student progress analytics and deterministic recommendations."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.models.learning_activity import LearningActivity
from backend.models.user import User
from backend.schemas.progress import (
    QuizAnalytics,
    TopicInsight,
    SkillGapSummary,
    RoadmapProgress,
    RecentActivitySummary,
    RecommendedAction,
    StudentProgressResponse,
)

logger = logging.getLogger(__name__)


def calculate_quiz_analytics(quiz_activities: list[LearningActivity]) -> QuizAnalytics:
    """Calculate aggregated quiz statistics and score trend from historical records."""
    if not quiz_activities:
        return QuizAnalytics(
            total_attempts=0,
            average_score=None,
            recent_score=None,
            highest_score=None,
            lowest_score=None,
            score_delta=None,
            trend="insufficient_data",
        )

    valid_scores: list[float] = []
    for act in quiz_activities:
        score = None
        if act.score is not None:
            try:
                score = float(act.score)
            except (ValueError, TypeError):
                pass
        elif act.data and isinstance(act.data, dict):
            eval_data = act.data.get("evaluation")
            if isinstance(eval_data, dict) and eval_data.get("score_percentage") is not None:
                try:
                    score = float(eval_data["score_percentage"])
                except (ValueError, TypeError):
                    pass

        if score is not None:
            score = max(0.0, min(100.0, score))
            valid_scores.append(round(score, 1))

    total_attempts = len(quiz_activities)
    if not valid_scores:
        return QuizAnalytics(
            total_attempts=total_attempts,
            average_score=None,
            recent_score=None,
            highest_score=None,
            lowest_score=None,
            score_delta=None,
            trend="insufficient_data",
        )

    avg_score = round(sum(valid_scores) / len(valid_scores), 1)
    recent_score = valid_scores[-1]
    highest_score = max(valid_scores)
    lowest_score = min(valid_scores)

    # Trend calculation requires >= 2 attempts to prevent false claims
    if len(valid_scores) < 2:
        return QuizAnalytics(
            total_attempts=total_attempts,
            average_score=avg_score,
            recent_score=recent_score,
        latest_score=recent_score,
            highest_score=highest_score,
            lowest_score=lowest_score,
            score_delta=None,
            trend="insufficient_data",
        )

    earliest_score = valid_scores[0]
    score_delta = round(recent_score - earliest_score, 1)

    if score_delta >= 5.0:
        trend = "improving"
    elif score_delta <= -5.0:
        trend = "declining"
    else:
        trend = "steady"

    return QuizAnalytics(
        total_attempts=total_attempts,
        average_score=avg_score,
        recent_score=recent_score,
        latest_score=recent_score,
        highest_score=highest_score,
        lowest_score=lowest_score,
        score_delta=score_delta,
        trend=trend,
    )


def calculate_topic_insights(quiz_activities: list[LearningActivity]) -> tuple[list[str], list[str], list[TopicInsight]]:
    """Determine weak, improving, and steady topics from quiz history and evaluation data."""
    topic_attempts: dict[str, list[float]] = defaultdict(list)
    explicit_weak_topics: set[str] = set()

    for act in quiz_activities:
        score = None
        if act.score is not None:
            try:
                score = float(act.score)
            except (ValueError, TypeError):
                pass

        topic = None
        if act.data and isinstance(act.data, dict):
            raw_topic = act.data.get("topic")
            if raw_topic and isinstance(raw_topic, str) and raw_topic.strip():
                topic = raw_topic.strip()

            eval_dict = act.data.get("evaluation")
            if isinstance(eval_dict, dict):
                if score is None and eval_dict.get("score") is not None:
                    try:
                        score = float(eval_dict["score"])
                    except (ValueError, TypeError):
                        pass

                raw_weak = eval_dict.get("weak_topics", [])
                if isinstance(raw_weak, list):
                    for w in raw_weak:
                        if w and isinstance(w, str) and w.strip():
                            explicit_weak_topics.add(w.strip())

        if not topic and act.title and isinstance(act.title, str):
            clean_title = act.title.replace("Quiz Evaluation:", "").replace("Quiz:", "").strip()
            if clean_title:
                topic = clean_title

        if topic and score is not None:
            topic_attempts[topic].append(round(score, 1))

    topic_insights: list[TopicInsight] = []
    weak_topics: list[str] = []
    improving_topics: list[str] = []

    for topic, scores in topic_attempts.items():
        attempts_count = len(scores)
        topic_avg = round(sum(scores) / attempts_count, 1)
        latest = scores[-1]

        if attempts_count >= 2:
            delta = round(latest - scores[0], 1)
            if delta >= 10.0:
                t_trend = "improving"
            elif delta <= -10.0:
                t_trend = "declining"
            else:
                t_trend = "steady"
        else:
            delta = None
            t_trend = "insufficient_data"

        is_weak = (topic_avg < 70.0 or latest < 60.0 or topic in explicit_weak_topics)
        is_improving = (t_trend == "improving" or (attempts_count >= 2 and latest >= 75.0 and scores[0] < 70.0))

        if is_weak and not is_improving:
            weak_topics.append(topic)
        elif is_improving:
            improving_topics.append(topic)

        topic_insights.append(
            TopicInsight(
                topic=topic,
                attempts_count=attempts_count,
                average_score=topic_avg,
                latest_score=latest,
                score_delta=delta,
                trend=t_trend,
                status="weak" if is_weak else ("improving" if is_improving else "steady"),
            )
        )

    for w in sorted(explicit_weak_topics):
        if w not in weak_topics and w not in improving_topics:
            weak_topics.append(w)

    return weak_topics[:10], improving_topics[:10], topic_insights


def calculate_roadmap_progress(roadmap_activities: list[LearningActivity]) -> RoadmapProgress | None:
    """Analyze the latest roadmap activity to extract milestone progress and completion percentage."""
    if not roadmap_activities:
        return None

    latest_roadmap = roadmap_activities[-1]
    data = latest_roadmap.data if isinstance(latest_roadmap.data, dict) else {}

    raw_steps = data.get("steps", [])
    if not isinstance(raw_steps, list) or len(raw_steps) == 0:
        return RoadmapProgress(
            has_roadmap=True,
            title=latest_roadmap.title or "Learning Roadmap",
            total_milestones=0,
            completed_milestones=0,
            remaining_milestones=0,
            completion_percentage=0.0,
            next_milestone=None,
            completed_milestones_list=[],
            pending_milestones_list=[],
        )

    completed_list: list[str] = []
    pending_list: list[str] = []

    for step in raw_steps:
        if isinstance(step, dict):
            name = (
                step.get("milestone")
                or step.get("title")
                or step.get("topic")
                or "Milestone"
            )
            is_completed = bool(
                step.get("completed") is True
                or str(step.get("status", "")).lower() in ("completed", "done")
            )
            if is_completed:
                completed_list.append(str(name).strip())
            else:
                pending_list.append(str(name).strip())

    total_m = len(completed_list) + len(pending_list)
    completed_m = len(completed_list)
    remaining_m = len(pending_list)

    if total_m > 0:
        pct = round((completed_m / total_m) * 100.0, 1)
    else:
        pct = 0.0

    next_milestone = pending_list[0] if pending_list else None

    return RoadmapProgress(
        has_roadmap=True,
        title=latest_roadmap.title or "Learning Roadmap",
        total_milestones=total_m,
        completed_milestones=completed_m,
        remaining_milestones=remaining_m,
        completion_percentage=pct,
        next_milestone=next_milestone,
        completed_milestones_list=completed_list,
        pending_milestones_list=pending_list,
    )


def extract_skill_gaps(assessment_activities: list[LearningActivity]) -> list[SkillGapSummary]:
    """Extract prioritized skill gaps identified in the latest assessment."""
    if not assessment_activities:
        return []

    latest_assessment = assessment_activities[-1]
    data = latest_assessment.data if isinstance(latest_assessment.data, dict) else {}
    gaps_raw = data.get("skill_gaps", [])

    summaries: list[SkillGapSummary] = []
    if isinstance(gaps_raw, list):
        for g in gaps_raw:
            if isinstance(g, dict) and (g.get("skill_name") or g.get("skill")):
                name = g.get("skill_name") or g.get("skill")
                if name:
                    summaries.append(
                        SkillGapSummary(
                            skill_name=str(name).strip(),
                            priority=str(g.get("priority", "medium")).lower(),
                            current_level=str(g.get("current_level")) if g.get("current_level") else None,
                            target_level=str(g.get("required_level") or g.get("target_level")) if (g.get("required_level") or g.get("target_level")) else None,
                        )
                    )

    priority_order = {"high": 1, "medium": 2, "low": 3}
    summaries.sort(key=lambda x: priority_order.get(x.priority, 4))
    return summaries[:10]


def generate_recommended_actions(
    has_assessment: bool,
    roadmap_progress: RoadmapProgress | None,
    quiz_analytics: QuizAnalytics,
    weak_topics: list[str],
    improving_topics: list[str],
    skill_gaps: list[SkillGapSummary],
) -> list[RecommendedAction]:
    """Generate deterministic, evidence-based recommendations for next student actions."""
    actions: list[RecommendedAction] = []

    # Priority 1: Weak topics identified from recent quizzes (urgent intervention)
    if weak_topics:
        top_weak = weak_topics[0]
        actions.append(
            RecommendedAction(
                priority=1,
                action_type="targeted_revision",
                title=f"Review '{top_weak}' with AI Tutor",
                description=f"You had difficulty with {top_weak} in recent quiz attempts. Ask the AI Tutor for explanations and examples.",
                target_route="/tutor",
                context={
                    "topic": top_weak,
                    "question": f"Can you explain the key concepts of {top_weak} and give examples to help me improve on what I missed?",
                },
            )
        )
        actions.append(
            RecommendedAction(
                priority=2,
                action_type="practice_quiz",
                title=f"Practice Quiz on '{top_weak}'",
                description=f"Retake or practice a focused quiz on {top_weak} to confirm your understanding.",
                target_route="/quiz",
                context={"topic": top_weak},
            )
        )

    # Priority 2: No assessment taken yet
    if not has_assessment:
        actions.append(
            RecommendedAction(
                priority=1 if not weak_topics else 2,
                action_type="initial_assessment",
                title="Complete Your Initial Skill Assessment",
                description="Evaluate your current abilities against industry expectations to generate your learning baseline.",
                target_route="/assessment",
                context={},
            )
        )

    # Priority 3: Assessment completed, but no roadmap generated
    if has_assessment and (roadmap_progress is None or not roadmap_progress.has_roadmap):
        actions.append(
            RecommendedAction(
                priority=1,
                action_type="create_roadmap",
                title="Generate Your Personalized Learning Roadmap",
                description="Turn your assessment results into a structured step-by-step path toward your career goal.",
                target_route="/roadmap",
                context={},
            )
        )
        top_weak = weak_topics[0]
        actions.append(
            RecommendedAction(
                priority=1,
                action_type="targeted_revision",
                title=f"Review '{top_weak}' with AI Tutor",
                description=f"You had difficulty with {top_weak} in recent quiz attempts. Ask the AI Tutor for explanations and examples.",
                target_route="/tutor",
                context={
                    "topic": top_weak,
                    "question": f"Can you explain the key concepts of {top_weak} and give examples to help me improve on what I missed?",
                },
            )
        )
        actions.append(
            RecommendedAction(
                priority=2,
                action_type="practice_quiz",
                title=f"Practice Quiz on '{top_weak}'",
                description=f"Retake or practice a focused quiz on {top_weak} to confirm your understanding.",
                target_route="/quiz",
                context={"topic": top_weak},
            )
        )

    # Priority 4: No quiz history at all
    if quiz_analytics.total_attempts == 0 and not weak_topics:
        target_topic = (
            roadmap_progress.next_milestone
            if (roadmap_progress and roadmap_progress.has_roadmap and roadmap_progress.next_milestone)
            else "Diagnostic Fundamentals"
        )
        actions.append(
            RecommendedAction(
                priority=2,
                action_type="diagnostic_quiz",
                title=f"Take a Diagnostic Quiz on '{target_topic}'",
                description="Test your baseline knowledge to establish progress tracking and identify improvement areas.",
                target_route="/quiz",
                context={"topic": target_topic},
            )
        )

    # Priority 5: Advancing through roadmap milestones
    if (
        roadmap_progress
        and roadmap_progress.has_roadmap
        and roadmap_progress.remaining_milestones > 0
        and not weak_topics
    ):
        next_m = roadmap_progress.next_milestone or "Next Milestone"
        actions.append(
            RecommendedAction(
                priority=2,
                action_type="advance_milestone",
                title=f"Work on Milestone: {next_m}",
                description="Continue making progress toward completing your current learning roadmap step.",
                target_route="/roadmap",
                context={"milestone": next_m},
            )
        )

    # Priority 6: All roadmap milestones completed
    if (
        roadmap_progress
        and roadmap_progress.has_roadmap
        and roadmap_progress.total_milestones > 0
        and roadmap_progress.remaining_milestones == 0
    ):
        actions.append(
            RecommendedAction(
                priority=1,
                action_type="mastery_assessment",
                title="Evaluate Your New Skill Mastery",
                description="Congratulations on finishing all milestones! Take a follow-up assessment to benchmark your growth.",
                target_route="/assessment",
                context={},
            )
        )

    return actions[:3]


def calculate_student_progress(
    activities: list[LearningActivity],
    user_id: int = 1,
    student_name: str = "Student",
) -> StudentProgressResponse:
    """Pure calculation of student progress from an in-memory list of activities."""
    total_activities = len(activities)
    has_history = total_activities > 0

    quiz_activities = [a for a in activities if a.activity_type == "quiz"]
    roadmap_activities = [a for a in activities if a.activity_type == "roadmap"]
    assessment_activities = [a for a in activities if a.activity_type == "assessment"]

    # 1. Quiz Analytics
    quiz_analytics = calculate_quiz_analytics(quiz_activities)

    # 2. Topic Insights & Weak Topics
    weak_topics, improving_topics, topic_insights = calculate_topic_insights(quiz_activities)

    # 3. Roadmap Progress
    roadmap_progress = calculate_roadmap_progress(roadmap_activities)

    # 4. Skill Gaps from Assessment
    skill_gaps = extract_skill_gaps(assessment_activities)
    has_assessment = len(assessment_activities) > 0

    # 5. Recent activities (latest 5, newest first)
    recent_activities: list[RecentActivitySummary] = []
    for idx, act in enumerate(reversed(activities[-5:])):
        created_time = getattr(act, "created_at", None)
        if not created_time:
            created_time = datetime.now(timezone.utc)
        score_val = None
        if act.score is not None:
            try:
                score_val = float(act.score)
            except (ValueError, TypeError):
                score_val = None
        recent_activities.append(
            RecentActivitySummary(
                id=getattr(act, "id", None) or (idx + 1),
                activity_type=act.activity_type or "unknown",
                title=act.title or "",
                summary=act.summary,
                score=score_val,
                created_at=created_time,
            )
        )

    # 6. Evidence-based Recommended Actions
    recommended_actions = generate_recommended_actions(
        has_assessment=has_assessment,
        roadmap_progress=roadmap_progress,
        quiz_analytics=quiz_analytics,
        weak_topics=weak_topics,
        improving_topics=improving_topics,
        skill_gaps=skill_gaps,
    )

    return StudentProgressResponse(
        user_id=user_id,
        student_name=student_name,
        has_history=has_history,
        total_activities=total_activities,
        quiz_analytics=quiz_analytics,
        weak_topics=weak_topics,
        improving_topics=improving_topics,
        topic_insights=topic_insights,
        skill_gaps=skill_gaps,
        roadmap_progress=roadmap_progress,
        recent_activities=recent_activities,
        recommended_actions=recommended_actions,
    )


def get_student_progress(db: Session, user: User) -> StudentProgressResponse:
    """Retrieve full student progress intelligence scoped strictly to the authenticated user."""
    activities = (
        db.query(LearningActivity)
        .filter(LearningActivity.user_id == user.id)
        .order_by(LearningActivity.created_at.asc())
        .all()
    )

    return calculate_student_progress(
        activities=activities,
        user_id=user.id,
        student_name=user.full_name or "Student",
    )
