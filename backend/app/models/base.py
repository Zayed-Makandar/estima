from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class TimestampMixin:
    """Mixin for created_at and updated_at fields - use as first base class."""
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
