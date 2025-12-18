from typing import List, Literal, Optional

from pydantic import BaseModel, Field


MarketplaceName = Literal["robu", "robocraze", "thinkrobotics", "evelta"]


class MarketplaceQuery(BaseModel):
    marketplace: MarketplaceName
    query: str = Field(..., description="Search text for the product")
    limit: int = Field(5, ge=1, le=25)


class MultiMarketplaceQuery(BaseModel):
    query: str = Field(..., description="Search text for the product")
    limit: int = Field(6, ge=1, le=25, description="Max items per marketplace")
    marketplaces: Optional[List[MarketplaceName]] = Field(None, description="Subset of marketplaces; defaults to all")


class MarketplaceItem(BaseModel):
    title: str
    price_text: str
    availability: str
    url: str
    source: MarketplaceName
    image_url: str = ""
    sku: str = ""


class MarketplaceSearchResponse(BaseModel):
    items: List[MarketplaceItem]
    fetched_at: str
    note: Optional[str] = None
    from_cache: bool = False


class RefreshItemRequest(BaseModel):
    url: str = Field(..., description="Product URL to refresh")
    source: MarketplaceName


class RefreshItemResponse(BaseModel):
    title: str
    price_text: str
    availability: str
    url: str
    source: MarketplaceName
    image_url: str = ""
    refreshed_at: str
