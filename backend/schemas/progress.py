"""Pydantic schemas for student progress analytics and intelligence."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class QuizAnalytics(BaseModel):
    total_attempts: int = Field(default=0, ge=0)
    average_score: float | None = Field(default=None)
    recent_score: float | None = Field(default=None)
    highest_score: float | None = Field(default=None)
    lowest_score: float | None = Field(default=None)
    score_delta: float | None = Field(
        default=None,
        description="Difference between recent score and earliest recorded score. None if fewer than 2 attempts."
    )
    trend: Literal["improving", "declining", "steady", "insufficient_data"] = "insufficient_data"


class TopicInsight(BaseModel):
    topic: str
    status: Literal["weak", "improving", "mastered", "needs_practice", "steady"] = "needs_practice"
    attempts_count: int = Field(default=1, ge=1)
    average_score: float | None = None
    latest_score: float | None = None
    score_delta: float | None = None
    trend: Literal["improving", "declining", "steady", "insufficient_data"] = "insufficient_data"


class SkillGapSummary(BaseModel):
    skill_name: str
    priority: str = "medium"
    current_level: str | None = None
    target_level: str | None = None


class RoadmapProgress(BaseModel):
    has_roadmap: bool = False
    title: str | None = None
    total_milestones: int = Field(default=0, ge=0)
    completed_milestones: int = Field(default=0, ge=0)
    remaining_milestones: int = Field(default=0, ge=0)
    completion_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    next_milestone: str | None = None
    is_tracked: bool = False
    completed_milestones_list: list[str] = Field(default_factory=list)
    pending_milestones_list: list[str] = Field(default_factory=list)


class RecentActivitySummary(BaseModel):
    id: int
    activity_type: str
    title: str
    summary: str | None = None
    score: float | None = None
    created_at: datetime


class RecommendedAction(BaseModel):
    priority: int = Field(default=1, ge=1, le=5)
    action_type: str = Field(..., description="Action category, e.g. targeted_revision, practice_quiz, advance_milestone")
    title: str
    description: str
    target_route: str
    context: dict[str, Any] = Field(default_factory=dict)


class StudentProgressResponse(BaseModel):
    user_id: int
    student_name: str
    has_history: bool = False
    total_activities: int = Field(default=0, ge=0)
    quiz_analytics: QuizAnalytics
    weak_topics: list[str] = Field(default_factory=list)
    improving_topics: list[str] = Field(default_factory=list)
    topic_insights: list[TopicInsight] = Field(default_factory=list)
    skill_gaps: list[SkillGapSummary] = Field(default_factory=list)
    roadmap_progress: RoadmapProgress | None = None
    recent_activities: list[RecentActivitySummary] = Field(default_factory=list)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
