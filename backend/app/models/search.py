from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class SearchResult(SQLModel, table=True):
    """Cached search results with 7-day expiration."""
    id: Optional[int] = Field(default=None, primary_key=True)
    query_normalized: str = Field(index=True)  # lowercase, trimmed
    items_json: str  # JSON serialized list of items
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime  # created_at + 7 days
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class UserSearchHistory(SQLModel, table=True):
    """Links users to their search history."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    search_result_id: int = Field(foreign_key="searchresult.id", index=True)
    searched_at: datetime = Field(default_factory=datetime.utcnow)


class SearchQueryLog(SQLModel, table=True):
    """Logs all search queries for recommendations."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    query_text: str = Field(index=True)  # Original query text
    search_result_id: Optional[int] = Field(foreign_key="searchresult.id")
    searched_at: datetime = Field(default_factory=datetime.utcnow)
