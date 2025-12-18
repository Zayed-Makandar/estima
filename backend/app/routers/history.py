import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth.dependencies import get_current_user
from ..db.session import get_session
from ..models.search import SearchResult, UserSearchHistory
from ..models.user import User

router = APIRouter(prefix="/api/history", tags=["history"])


class HistoryItemResponse(BaseModel):
    id: int
    query: str
    items_count: int
    searched_at: str
    note: str | None = None


class HistoryDetailResponse(BaseModel):
    id: int
    query: str
    items: list
    searched_at: str
    note: str | None = None


@router.get("", response_model=List[HistoryItemResponse])
def get_history(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> List[HistoryItemResponse]:
    """Get current user's search history."""
    stmt = (
        select(UserSearchHistory, SearchResult)
        .join(SearchResult, UserSearchHistory.search_result_id == SearchResult.id)
        .where(UserSearchHistory.user_id == user.id)
        .order_by(UserSearchHistory.searched_at.desc())
        .limit(50)
    )
    results = session.exec(stmt).all()
    
    history = []
    for ush, sr in results:
        items = json.loads(sr.items_json) if sr.items_json else []
        history.append(HistoryItemResponse(
            id=ush.id,
            query=sr.query_normalized,
            items_count=len(items),
            searched_at=ush.searched_at.isoformat(),
            note=sr.note,
        ))
    
    return history


@router.get("/{history_id}", response_model=HistoryDetailResponse)
def get_history_detail(
    history_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> HistoryDetailResponse:
    """Get a specific history item with full results."""
    stmt = (
        select(UserSearchHistory, SearchResult)
        .join(SearchResult, UserSearchHistory.search_result_id == SearchResult.id)
        .where(UserSearchHistory.id == history_id, UserSearchHistory.user_id == user.id)
    )
    result = session.exec(stmt).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History item not found",
        )
    
    ush, sr = result
    items = json.loads(sr.items_json) if sr.items_json else []
    
    return HistoryDetailResponse(
        id=ush.id,
        query=sr.query_normalized,
        items=items,
        searched_at=ush.searched_at.isoformat(),
        note=sr.note,
    )


@router.delete("/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history_item(
    history_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    """Delete a history item for the current user."""
    ush = session.exec(
        select(UserSearchHistory).where(
            UserSearchHistory.id == history_id,
            UserSearchHistory.user_id == user.id,
        )
    ).first()
    
    if not ush:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History item not found",
        )
    
    session.delete(ush)
    session.commit()
