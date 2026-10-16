"""Route for student learning progress analytics and intelligence."""

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.core.rate_limit import rate_limit_user
from backend.database.session import get_db
from backend.models.user import User
from backend.schemas.progress import StudentProgressResponse
from backend.services.progress_service import get_student_progress

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/progress",
    tags=["Progress Intelligence"],
)


@router.get(
    "",
    response_model=StudentProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated student's learning progress analytics and recommendations",
)
def get_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(
        rate_limit_user(max_requests=60, window_seconds=60, group="progress")
    ),
) -> StudentProgressResponse:
    """Compute and return evidence-based progress analytics strictly scoped to current_user."""
    try:
        return get_student_progress(db=db, user=current_user)
    except Exception as exc:
        logger.error("Failed to generate student progress for user %s: %s", current_user.id, exc, exc_info=True)
        # Fallback to empty response rather than crashing or exposing stack traces
        from backend.schemas.progress import QuizAnalytics, RoadmapProgress
        return StudentProgressResponse(
            user_id=current_user.id,
            student_name=current_user.full_name or "Student",
            has_history=False,
            total_activities=0,
            quiz_analytics=QuizAnalytics(),
            weak_topics=[],
            improving_topics=[],
            topic_insights=[],
            skill_gaps=[],
            roadmap_progress=RoadmapProgress(has_roadmap=False),
            recent_activities=[],
            recommended_actions=[],
        )
