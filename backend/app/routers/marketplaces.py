import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..adapters import ALL_ADAPTERS
from ..auth.dependencies import get_current_user
from ..db.session import get_session
from ..models.search import SearchResult, UserSearchHistory, SearchQueryLog
from ..models.user import User
from ..schemas.marketplace import (
    MarketplaceName,
    MarketplaceQuery,
    MarketplaceSearchResponse,
    MultiMarketplaceQuery,
)
from ..services.playwright import PlaywrightService

router = APIRouter(prefix="/api/marketplaces", tags=["marketplaces"])

_service: Optional[PlaywrightService] = None
CACHE_DAYS = 7


def get_playwright_service() -> PlaywrightService:
    global _service
    if _service is None:
        _service = PlaywrightService()
    return _service


def normalize_query(query: str) -> str:
    """Normalize query for cache lookup."""
    return query.lower().strip()


def filter_blog_urls(items: List[Dict]) -> List[Dict]:
    """Filter out ThinkRobotics blog pages from results."""
    filtered = []
    for item in items:
        url = item.get("url", "")
        # Skip ThinkRobotics blog pages
        if "/blogs/" in url:
            continue
        filtered.append(item)
    return filtered


def get_cached_result(session: Session, query: str) -> Optional[SearchResult]:
    """Get cached result if not expired."""
    normalized = normalize_query(query)
    stmt = select(SearchResult).where(
        SearchResult.query_normalized == normalized,
        SearchResult.expires_at > datetime.utcnow(),
    )
    return session.exec(stmt).first()


def save_search_result(
    session: Session,
    query: str,
    items: List[Dict],
    note: Optional[str],
) -> SearchResult:
    """Save search result to cache."""
    normalized = normalize_query(query)
    now = datetime.utcnow()
    
    sr = SearchResult(
        query_normalized=normalized,
        items_json=json.dumps(items),
        fetched_at=now,
        expires_at=now + timedelta(days=CACHE_DAYS),
        note=note,
    )
    session.add(sr)
    session.commit()
    session.refresh(sr)
    return sr


def log_user_search(
    session: Session,
    user: User,
    query: str,
    search_result: SearchResult,
) -> None:
    """Log the search for user history and recommendations."""
    # Create user search history entry
    ush = UserSearchHistory(
        user_id=user.id,
        search_result_id=search_result.id,
        searched_at=datetime.utcnow(),
    )
    session.add(ush)
    
    # Create search query log for recommendations
    sql = SearchQueryLog(
        user_id=user.id,
        query_text=query.strip(),
        search_result_id=search_result.id,
        searched_at=datetime.utcnow(),
    )
    session.add(sql)
    session.commit()


@router.post("/search", response_model=MarketplaceSearchResponse)
async def search_marketplace(
    payload: MarketplaceQuery,
    user: User = Depends(get_current_user),
    playwright: PlaywrightService = Depends(get_playwright_service),
    session: Session = Depends(get_session),
) -> MarketplaceSearchResponse:
    if payload.marketplace not in ALL_ADAPTERS:
        raise HTTPException(status_code=400, detail="Unsupported marketplace")

    adapter = ALL_ADAPTERS[payload.marketplace]
    result = await playwright.search(adapter, payload.query, limit=payload.limit, source_key=payload.marketplace)
    
    # Filter blog URLs
    items = filter_blog_urls(result["items"])

    note = result.get("note") or f"Sourced from {adapter['name']}"
    return MarketplaceSearchResponse(
        items=items,
        fetched_at=result.get("fetched_at", datetime.utcnow().isoformat()),
        note=note,
        from_cache=False,
    )


@router.post("/search_all", response_model=MarketplaceSearchResponse)
async def search_all_marketplaces(
    payload: MultiMarketplaceQuery,
    user: User = Depends(get_current_user),
    playwright: PlaywrightService = Depends(get_playwright_service),
    session: Session = Depends(get_session),
) -> MarketplaceSearchResponse:
    # Determine which marketplaces to search
    marketplace_keys: List[MarketplaceName] = (
        payload.marketplaces if payload.marketplaces else list(ALL_ADAPTERS.keys())
    )
    
    # Only use cache if searching ALL marketplaces
    # When specific marketplaces are selected, always search fresh
    use_cache = payload.marketplaces is None or len(payload.marketplaces) == len(ALL_ADAPTERS)
    
    if use_cache:
        # Check cache first
        cached = get_cached_result(session, payload.query)
        if cached:
            items = json.loads(cached.items_json)
            # Log this search for the user
            log_user_search(session, user, payload.query, cached)
            return MarketplaceSearchResponse(
                items=items,
                fetched_at=cached.fetched_at.isoformat(),
                note=cached.note or "From cache",
                from_cache=True,
            )

    async def run_search(key: MarketplaceName):
        adapter = ALL_ADAPTERS[key]
        try:
            return key, await playwright.search(adapter, payload.query, limit=payload.limit, source_key=key)
        except Exception as exc:
            return key, {"items": [], "note": f"{adapter['name']} failed: {exc}"}

    results = await asyncio.gather(*(run_search(key) for key in marketplace_keys))

    items = []
    notes = []
    for key, res in results:
        if not res:
            continue
        items.extend(res.get("items", []))
        if res.get("note"):
            notes.append(f"{key}: {res['note']}")

    # Filter blog URLs
    items = filter_blog_urls(items)

    def price_value(item: Dict) -> float:
        txt = (item.get("price_text") or "").replace(",", "")
        match = re.search(r"(\d+(?:\.\d+)?)", txt)
        try:
            return float(match.group(1)) if match else float("inf")
        except Exception:
            return float("inf")

    items.sort(key=price_value)
    items = items[: payload.limit * len(marketplace_keys)]
    
    fetched_at = datetime.utcnow().isoformat()
    note = "; ".join(notes) if notes else "Aggregated results"
    
    # Save to cache
    sr = save_search_result(session, payload.query, items, note)
    
    # Log for user history
    log_user_search(session, user, payload.query, sr)
    
    return MarketplaceSearchResponse(
        items=items,
        fetched_at=fetched_at,
        note=note,
        from_cache=False,
    )
