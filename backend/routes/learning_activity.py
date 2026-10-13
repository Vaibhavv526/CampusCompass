from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db
from backend.models.user import User
from backend.schemas.learning_activity import (
    LearningActivityCreate,
    LearningActivityResponse,
    LearningActivityUpdate,
)
from backend.services import learning_activity_service

router = APIRouter(
    prefix="/api/learning-history",
    tags=["Learning History"],
)


@router.post(
    "",
    response_model=LearningActivityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_learning_activity(
    activity_data: LearningActivityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return learning_activity_service.create_activity(
        db=db,
        user_id=current_user.id,
        activity_data=activity_data,
    )


@router.get(
    "",
    response_model=list[LearningActivityResponse],
)
def get_learning_history(
    activity_type: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return learning_activity_service.get_user_activities(
        db=db,
        user_id=current_user.id,
        activity_type=activity_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{activity_id}",
    response_model=LearningActivityResponse,
)
def get_learning_activity(
    activity_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    activity = learning_activity_service.get_activity_by_id(
        db=db,
        user_id=current_user.id,
        activity_id=activity_id,
    )

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning activity not found.",
        )

    return activity


@router.patch(
    "/{activity_id}",
    response_model=LearningActivityResponse,
)
def update_learning_activity(
    activity_id: int,
    update_data: LearningActivityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = learning_activity_service.update_activity(
        db=db,
        user_id=current_user.id,
        activity_id=activity_id,
        update_data=update_data,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning activity not found.",
        )

    return updated


@router.delete(
    "/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_learning_activity(
    activity_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = learning_activity_service.delete_activity(
        db=db,
        user_id=current_user.id,
        activity_id=activity_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning activity not found.",
        )

    return None
