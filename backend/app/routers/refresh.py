from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..auth.dependencies import get_current_user
from ..db.session import get_session
from ..models.user import User
from ..schemas.marketplace import RefreshItemRequest, RefreshItemResponse
from ..services.playwright import PlaywrightService

router = APIRouter(prefix="/api/items", tags=["items"])

_service: Optional[PlaywrightService] = None


def get_playwright_service() -> PlaywrightService:
    global _service
    if _service is None:
        _service = PlaywrightService()
    return _service


@router.post("/refresh", response_model=RefreshItemResponse)
async def refresh_item(
    payload: RefreshItemRequest,
    user: User = Depends(get_current_user),
    playwright: PlaywrightService = Depends(get_playwright_service),
) -> RefreshItemResponse:
    """Refresh a single item by fetching current data from its product page."""
    
    # Validate URL
    parsed = urlparse(payload.url)
    if not parsed.scheme or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid URL")
    
    # Fetch current data from product page
    try:
        item_data = await playwright.refresh_single_item(payload.url, payload.source)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh item: {str(e)}")
    
    if not item_data:
        raise HTTPException(status_code=404, detail="Could not extract item data from URL")
    
    return RefreshItemResponse(
        title=item_data.get("title", ""),
        price_text=item_data.get("price_text", ""),
        availability=item_data.get("availability", ""),
        url=payload.url,
        source=payload.source,
        image_url=item_data.get("image_url", ""),
        sku=item_data.get("sku", ""),
        refreshed_at=datetime.utcnow().isoformat(),
    )
