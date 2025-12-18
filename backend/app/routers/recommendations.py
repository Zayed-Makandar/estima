from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select, func

from ..auth.dependencies import get_current_user
from ..db.session import get_session
from ..models.search import SearchQueryLog, SearchResult
from ..models.user import User

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


class RecommendationResponse(BaseModel):
    query: str
    search_count: int
    has_cached_results: bool


@router.get("", response_model=List[RecommendationResponse])
def get_recommendations(
    q: str = Query("", description="Partial query to match"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> List[RecommendationResponse]:
    """Get search recommendations based on all users' previous searches."""
    if not q or len(q) < 2:
        return []
    
    # Find matching queries from all users, grouped by query text
    # Use LOWER for case-insensitive search
    stmt = (
        select(
            SearchQueryLog.query_text,
            func.count(SearchQueryLog.id).label("search_count"),
            SearchQueryLog.search_result_id,
        )
        .where(func.lower(SearchQueryLog.query_text).contains(q.lower()))
        .group_by(SearchQueryLog.query_text, SearchQueryLog.search_result_id)
        .order_by(func.count(SearchQueryLog.id).desc())
        .limit(10)
    )
    
    results = session.exec(stmt).all()
    
    recommendations = []
    seen_queries = set()
    
    for query_text, count, result_id in results:
        normalized = query_text.lower().strip()
        if normalized in seen_queries:
            continue
        seen_queries.add(normalized)
        
        # Check if cached result is still valid
        has_cache = False
        if result_id:
            sr = session.get(SearchResult, result_id)
            if sr:
                from datetime import datetime
                has_cache = sr.expires_at > datetime.utcnow()
        
        recommendations.append(RecommendationResponse(
            query=query_text,
            search_count=count,
            has_cached_results=has_cache,
        ))
    
    return recommendations[:5]  # Return top 5
