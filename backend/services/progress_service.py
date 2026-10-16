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
    MilestoneMastery,
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


def normalize_text(text: str | None) -> str:
    """Normalize text by stripping, lowercasing, and removing common activity prefixes."""
    if not text:
        return ""
    t = text.strip().lower()
    for prefix in ("quiz on ", "quiz:", "practice quiz on ", "practice quiz:", "milestone:", "ai tutor:"):
        if t.startswith(prefix):
            t = t[len(prefix):].strip()
    return t


def calculate_milestone_mastery(
    raw_steps: list[dict],
    quiz_activities: list[LearningActivity],
    tutor_activities: list[LearningActivity],
    weak_topics: list[str],
) -> list[MilestoneMastery]:
    """
    Deterministically correlate roadmap milestones with quiz & tutor evidence.

    Mastery rules (approved Phase 3.4 product decisions):
    1. Latest quiz score >= 70%: MASTERED
    2. Latest quiz score < 60%, or a verified weak-topic signal: NEEDS_REVIEW
    3. Score 60-69%: IN_PROGRESS
    4. No reliable quiz evidence: NOT_STARTED, unless tutor activity supports IN_PROGRESS
    5. Completed status is advisory; display review_warning when evidence indicates weak performance.
    """
    if not raw_steps or not isinstance(raw_steps, list):
        return []

    # Count how many steps each skill belongs to across this roadmap.
    # A skill appearing in multiple steps is ambiguous and cannot reliably match without title/milestone match.
    skill_step_count: dict[str, int] = defaultdict(int)
    parsed_steps = []

    for idx, step in enumerate(raw_steps):
        if not isinstance(step, dict):
            continue
        title = str(
            step.get("milestone")
            or step.get("title")
            or step.get("topic")
            or f"Milestone {idx + 1}"
        ).strip()
        completed = bool(
            step.get("completed") is True
            or str(step.get("status", "")).lower() in ("completed", "done")
        )
        raw_skills = step.get("skills", [])
        if isinstance(raw_skills, list):
            skills = [str(s).strip() for s in raw_skills if s and str(s).strip()]
        elif isinstance(raw_skills, str):
            skills = [s.strip() for s in raw_skills.split(",") if s.strip()]
        else:
            skills = []

        try:
            hours = float(step.get("estimated_hours", 0.0) or 0.0)
        except (ValueError, TypeError):
            hours = 0.0

        for s in skills:
            skill_step_count[normalize_text(s)] += 1

        parsed_steps.append({
            "index": idx,
            "title": title,
            "norm_title": normalize_text(title),
            "completed": completed,
            "skills": skills,
            "norm_skills": [normalize_text(s) for s in skills],
            "hours": hours,
        })

    norm_weak_topics = {normalize_text(w) for w in weak_topics if w}

    milestone_mastery_list: list[MilestoneMastery] = []

    for p_step in parsed_steps:
        m_index = p_step["index"]
        m_title = p_step["title"]
        m_norm_title = p_step["norm_title"]
        m_completed = p_step["completed"]
        m_skills = p_step["skills"]
        m_norm_skills = p_step["norm_skills"]
        m_hours = p_step["hours"]

        # Match quizzes to milestones
        matched_quizzes: list[LearningActivity] = []
        for q in quiz_activities:
            q_data = q.data if isinstance(q.data, dict) else {}
            q_milestone = normalize_text(q_data.get("milestone"))
            q_topic = normalize_text(q_data.get("topic"))
            if not q_topic and q.title:
                q_topic = normalize_text(q.title)

            # Match 1: Explicit milestone name in quiz data
            if q_milestone and q_milestone == m_norm_title:
                matched_quizzes.append(q)
                continue

            # Match 2: Quiz topic exactly equals milestone title
            if q_topic and q_topic == m_norm_title:
                matched_quizzes.append(q)
                continue

            # Match 3: Quiz topic matches a unique milestone skill (no cross-step ambiguity)
            if q_topic and q_topic in m_norm_skills:
                if skill_step_count.get(q_topic, 0) == 1:
                    matched_quizzes.append(q)
                    continue

        # Sort matched quizzes chronologically (oldest to newest)
        matched_quizzes.sort(key=lambda x: getattr(x, "created_at", None) or datetime.min.replace(tzinfo=timezone.utc))

        # Check for weak-topic signal
        has_weak_signal = (
            m_norm_title in norm_weak_topics
            or any(s in norm_weak_topics for s in m_norm_skills)
        )

        attempt_count = len(matched_quizzes)
        latest_score: float | None = None
        highest_score: float | None = None
        mastery_status = "NOT_STARTED"
        evidence_source = "none"

        if attempt_count > 0:
            evidence_source = "quiz"
            scores: list[float] = []
            for q in matched_quizzes:
                s_val = None
                if q.score is not None:
                    try:
                        s_val = float(q.score)
                    except (ValueError, TypeError):
                        pass
                if s_val is None and q.data and isinstance(q.data, dict):
                    eval_d = q.data.get("evaluation")
                    if isinstance(eval_d, dict) and eval_d.get("score") is not None:
                        try:
                            s_val = float(eval_d["score"])
                        except (ValueError, TypeError):
                            pass
                if s_val is not None:
                    scores.append(round(s_val, 1))

            if scores:
                latest_score = scores[-1]
                highest_score = max(scores)

            # Check if latest quiz specifically flagged weak topics for this milestone
            latest_quiz = matched_quizzes[-1]
            if latest_quiz.data and isinstance(latest_quiz.data, dict):
                eval_dict = latest_quiz.data.get("evaluation")
                if isinstance(eval_dict, dict):
                    q_weaks = [normalize_text(w) for w in eval_dict.get("weak_topics", []) if w]
                    if m_norm_title in q_weaks or any(s in q_weaks for s in m_norm_skills):
                        has_weak_signal = True

            # Determine mastery status
            if latest_score is not None:
                if latest_score < 60.0 or has_weak_signal:
                    mastery_status = "NEEDS_REVIEW"
                elif latest_score >= 70.0:
                    mastery_status = "MASTERED"
                else:  # 60 <= latest_score < 70
                    mastery_status = "IN_PROGRESS"
            else:
                mastery_status = "NEEDS_REVIEW" if has_weak_signal else "IN_PROGRESS"
        else:
            # Check tutor activities for in-progress evidence
            matched_tutors = []
            for t in tutor_activities:
                t_data = t.data if isinstance(t.data, dict) else {}
                t_topic = normalize_text(t_data.get("topic") or t.title)
                t_milestone = normalize_text(t_data.get("milestone"))
                if t_milestone and t_milestone == m_norm_title:
                    matched_tutors.append(t)
                elif t_topic and t_topic == m_norm_title:
                    matched_tutors.append(t)
                elif t_topic and t_topic in m_norm_skills and skill_step_count.get(t_topic, 0) == 1:
                    matched_tutors.append(t)

            if matched_tutors:
                evidence_source = "tutor"
                mastery_status = "IN_PROGRESS"
            else:
                evidence_source = "none"
                mastery_status = "NOT_STARTED"

        # Advisory review warning if completed but weak
        review_warning: str | None = None
        if m_completed and mastery_status == "NEEDS_REVIEW":
            if latest_score is not None:
                review_warning = (
                    f"Milestone is marked completed, but recorded quiz evidence indicates "
                    f"review is recommended (Latest Score: {round(latest_score)}%)."
                )
            else:
                review_warning = (
                    "Milestone is marked completed, but recorded quiz evaluation "
                    "indicates this area needs review."
                )

        milestone_mastery_list.append(
            MilestoneMastery(
                milestone_index=m_index,
                title=m_title,
                completed=m_completed,
                skills=m_skills,
                estimated_hours=m_hours,
                mastery_status=mastery_status,
                latest_score=latest_score,
                highest_score=highest_score,
                attempt_count=attempt_count,
                evidence_source=evidence_source,
                review_warning=review_warning,
            )
        )

    return milestone_mastery_list


def calculate_roadmap_progress(
    roadmap_activities: list[LearningActivity],
    quiz_activities: list[LearningActivity] | None = None,
    tutor_activities: list[LearningActivity] | None = None,
    weak_topics: list[str] | None = None,
) -> RoadmapProgress | None:
    """Analyze the latest roadmap activity to extract milestone progress, completion percentage, and mastery intelligence."""
    if not roadmap_activities:
        return None

    if quiz_activities is None:
        quiz_activities = []
    if tutor_activities is None:
        tutor_activities = []
    if weak_topics is None:
        weak_topics = []

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
            milestones=[],
            recommended_focus_milestone=None,
        )

    # Calculate deterministic milestone mastery
    milestones = calculate_milestone_mastery(
        raw_steps=raw_steps,
        quiz_activities=quiz_activities,
        tutor_activities=tutor_activities,
        weak_topics=weak_topics,
    )

    completed_list: list[str] = [m.title for m in milestones if m.completed]
    pending_list: list[str] = [m.title for m in milestones if not m.completed]

    total_m = len(milestones)
    completed_m = len(completed_list)
    remaining_m = len(pending_list)

    if total_m > 0:
        pct = round((completed_m / total_m) * 100.0, 1)
    else:
        pct = 0.0

    next_milestone = pending_list[0] if pending_list else None

    # Adaptive recommended focus milestone:
    # 1. Prioritize completed milestones that have reliable NEEDS_REVIEW evidence
    # 2. Otherwise recommend the next pending milestone
    recommended_focus: str | None = None
    for m in milestones:
        if m.completed and m.mastery_status == "NEEDS_REVIEW":
            recommended_focus = m.title
            break

    if not recommended_focus:
        recommended_focus = next_milestone

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
        milestones=milestones,
        recommended_focus_milestone=recommended_focus,
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

    # Priority 1A: Adaptive Roadmap Review - Completed milestones with reliable NEEDS_REVIEW evidence
    if roadmap_progress and roadmap_progress.has_roadmap:
        for m in roadmap_progress.milestones:
            if m.completed and m.mastery_status == "NEEDS_REVIEW":
                score_str = f"recorded quiz score was {round(m.latest_score)}%" if m.latest_score is not None else "recorded quiz evidence indicates this is a weak area"
                actions.append(
                    RecommendedAction(
                        priority=1,
                        action_type="milestone_review",
                        title=f"Review Completed Milestone: '{m.title}'",
                        description=f"You marked '{m.title}' as completed, but your {score_str}. Review concepts before advancing.",
                        target_route="/quiz",
                        context={
                            "topic": m.title,
                            "milestone": m.title,
                        },
                    )
                )

    # Priority 1B: Weak topics identified from recent quizzes (urgent intervention)
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

    # 3. Roadmap Progress (with deterministic milestone mastery correlation)
    tutor_activities = [a for a in activities if a.activity_type == "tutor"]
    roadmap_progress = calculate_roadmap_progress(
        roadmap_activities=roadmap_activities,
        quiz_activities=quiz_activities,
        tutor_activities=tutor_activities,
        weak_topics=weak_topics,
    )

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
