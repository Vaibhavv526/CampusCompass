from sqlalchemy.orm import Session

from backend.models.learning_activity import LearningActivity
from backend.schemas.learning_activity import (
    LearningActivityCreate,
    LearningActivityUpdate,
)


def create_activity(
    db: Session,
    user_id: int,
    activity_data: LearningActivityCreate,
) -> LearningActivity:
    activity = LearningActivity(
        user_id=user_id,
        activity_type=activity_data.activity_type,
        title=activity_data.title,
        summary=activity_data.summary,
        score=activity_data.score,
        data=activity_data.data,
    )

    db.add(activity)
    db.commit()
    db.refresh(activity)

    return activity


def get_user_activities(
    db: Session,
    user_id: int,
    activity_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[LearningActivity]:
    query = (
        db.query(LearningActivity)
        .filter(LearningActivity.user_id == user_id)
    )

    if activity_type:
        query = query.filter(LearningActivity.activity_type == activity_type)

    return (
        query.order_by(LearningActivity.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_activity_by_id(
    db: Session,
    user_id: int,
    activity_id: int,
) -> LearningActivity | None:
    return (
        db.query(LearningActivity)
        .filter(
            LearningActivity.id == activity_id,
            LearningActivity.user_id == user_id,
        )
        .first()
    )


def update_activity(
    db: Session,
    user_id: int,
    activity_id: int,
    update_data: LearningActivityUpdate,
) -> LearningActivity | None:
    activity = get_activity_by_id(db, user_id=user_id, activity_id=activity_id)
    if not activity:
        return None

    if update_data.summary is not None:
        activity.summary = update_data.summary
    if update_data.score is not None:
        activity.score = update_data.score
    if update_data.data is not None:
        activity.data = update_data.data

    db.commit()
    db.refresh(activity)

    return activity


def delete_activity(
    db: Session,
    user_id: int,
    activity_id: int,
) -> bool:
    activity = get_activity_by_id(db, user_id=user_id, activity_id=activity_id)
    if not activity:
        return False

    db.delete(activity)
    db.commit()
    return True
