from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class PurchaseOrder(SQLModel, table=True):
    """Purchase Order model for storing PO history and drafts."""
    __tablename__ = "purchase_orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    
    # PO Metadata
    po_number: str = Field(index=True)
    po_date: str
    status: str = Field(default="draft")  # draft, completed
    
    # Vendor details (stored as JSON string)
    vendor_name: str
    vendor_address: str = ""
    vendor_phone: str = ""
    vendor_email: str = ""
    vendor_gstin: str = ""
    vendor_pan: str = ""
    
    # Shipping address
    shipping_address: str = ""
    
    # Items (stored as JSON string)
    items_json: str = "[]"
    
    # Financial
    gst_rate: float = 18.0
    sub_total: float = 0.0
    gst_amount: float = 0.0
    grand_total: float = 0.0
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
