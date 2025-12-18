import os
import json
import tempfile
import base64
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import Session, select
import pdfkit

from ..db.session import get_session
from ..auth.dependencies import get_current_user, get_admin_user
from ..models import PurchaseOrder, User

router = APIRouter(prefix="/api/po", tags=["purchase_order"])

# ============================================================
# IMAGE CONFIGURATION - Modify paths and sizes here
# ============================================================
LOGO_PATH = "/home/zayed/estim/frontend/public/ats_logo.png"
SIGNATURE_PATH = "/home/zayed/estim/frontend/public/ats_signature.png"

# Image display sizes (in pixels)
LOGO_WIDTH = 155       # Logo width in PDF
LOGO_HEIGHT = 150  # Logo height in PDF
SIGNATURE_MAX_WIDTH = 100   # Maximum signature width
SIGNATURE_MAX_HEIGHT = 250   # Maximum signature height
# ============================================================


class POItem(BaseModel):
    sl_no: int
    description: str
    sku: Optional[str] = ""
    quantity: int
    unit_price: float
    total_price: float


class VendorDetails(BaseModel):
    name: str
    address: str
    phone: str
    email: str
    gstin: str
    pan: str


class PurchaseOrderRequest(BaseModel):
    po_number: str
    po_date: str
    vendor: VendorDetails
    shipping_address: str
    items: List[POItem]
    gst_rate: float = 18.0


def get_image_base64(path: str) -> str:
    """Convert image file to base64 data URI."""
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
            ext = path.split(".")[-1].lower()
            mime = "image/png" if ext == "png" else "image/jpeg"
            return f"data:{mime};base64,{data}"
    except Exception:
        return ""


def number_to_words(num: int) -> str:
    """Convert number to words (Indian format)."""
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
            "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    if num == 0:
        return "Zero"
    
    def convert_less_than_thousand(n: int) -> str:
        if n < 20:
            return ones[n]
        if n < 100:
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")
        return ones[n // 100] + " Hundred" + (" " + convert_less_than_thousand(n % 100) if n % 100 else "")
    
    if num < 1000:
        return convert_less_than_thousand(num)
    if num < 100000:
        return convert_less_than_thousand(num // 1000) + " Thousand" + (" " + convert_less_than_thousand(num % 1000) if num % 1000 else "")
    if num < 10000000:
        return convert_less_than_thousand(num // 100000) + " Lakh" + (" " + number_to_words(num % 100000) if num % 100000 else "")
    return convert_less_than_thousand(num // 10000000) + " Crore" + (" " + number_to_words(num % 10000000) if num % 10000000 else "")


def generate_po_html(data: PurchaseOrderRequest) -> str:
    """Generate HTML for Purchase Order."""
    # Calculate totals
    sub_total = sum(item.total_price for item in data.items)
    gst_amount = sub_total * (data.gst_rate / 100)
    grand_total = sub_total + gst_amount
    amount_in_words = number_to_words(round(grand_total)) + " Rupees Only"
    
    # Get images as base64
    logo_base64 = get_image_base64(LOGO_PATH)
    signature_base64 = get_image_base64(SIGNATURE_PATH)
    
    # Format date
    try:
        po_date = datetime.strptime(data.po_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except:
        po_date = data.po_date
    
    # Generate item rows
    item_rows = ""
    for item in data.items:
        item_rows += f"""
        <tr>
            <td style="text-align: center; padding: 6px; border: 1px solid #000;">{item.sl_no}</td>
            <td style="text-align: left; padding: 6px; border: 1px solid #000;">{item.description}</td>
            <td style="text-align: center; padding: 6px; border: 1px solid #000;">{item.sku or '-'}</td>
            <td style="text-align: center; padding: 6px; border: 1px solid #000;">{item.quantity}</td>
            <td style="text-align: right; padding: 6px 10px; border: 1px solid #000;">{item.unit_price:.2f}</td>
            <td style="text-align: right; padding: 6px 10px; border: 1px solid #000;">{item.total_price:.2f}</td>
        </tr>
        """
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{ size: A4; margin: 15mm; }}
        body {{ font-family: Arial, sans-serif; font-size: 10px; color: #000; line-height: 1.4; margin: 0; padding: 0; }}
        .header {{ display: table; width: 100%; margin-bottom: 15px; }}
        .header-left {{ display: table-cell; vertical-align: top; width: 60%; }}
        .header-right {{ display: table-cell; vertical-align: top; width: 40%; }}
        .logo {{ width: {LOGO_WIDTH}px; height: {LOGO_HEIGHT}px; }}
        .company-name {{ font-size: 14px; font-weight: bold; margin: 0 0 5px 0; }}
        .company-details {{ font-size: 9px; margin: 2px 0; }}
        .title {{ font-size: 24px; font-weight: bold; color: #1E3A8A; text-align: center; margin: 15px 0; letter-spacing: 1px; }}
        .info-container {{ display: table; width: 100%; margin-top: 15px; }}
        .info-block {{ display: table-cell; width: 48%; border: 1px solid #000; padding: 10px; font-size: 9px; vertical-align: top; }}
        .info-spacer {{ display: table-cell; width: 4%; }}
        .po-meta {{ text-align: right; margin-top: 10px; font-size: 10px; }}
        .items-table {{ width: 100%; margin-top: 15px; border-collapse: collapse; }}
        .items-table th {{ 
            background-color: #DBEAFE; 
            font-size: 10px; 
            font-weight: bold; 
            padding: 8px; 
            border: 1px solid #000; 
            text-transform: uppercase; 
        }}
        .summary-row td {{ font-weight: bold; font-size: 11px; padding: 8px 10px; border: 1px solid #000; }}
        .grand-total-row {{ background-color: #E3F2FD; }}
        .grand-total-row td {{ color: #1E3A8A; font-size: 12px; font-weight: bold; padding: 10px; border: 1px solid #000; }}
        .amount-words {{ font-size: 9px; font-style: italic; color: #374151; margin-top: 10px; }}
        .terms {{ width: 60%; margin-top: 20px; font-size: 8px; color: #374151; line-height: 1.6; padding: 15px; background-color: #F9FAFB; border: 1px solid #E5E7EB; }}
        .signature-block {{ width: 35%; margin-left: auto; margin-top: 30px; text-align: center; border: 1px solid #000; padding: 15px; }}
        .signature-img {{ max-width: {SIGNATURE_MAX_WIDTH}px; max-height: {SIGNATURE_MAX_HEIGHT}px; }}
    </style>
</head>
<body>
    <!-- Header with Logo -->
    <!-- Header with Logo -->
    <div class="header">
        <div class="header-left">
            {f'<img class="logo" src="{logo_base64}" alt="Logo">' if logo_base64 else f'<div style="width:{LOGO_WIDTH}px;height:{LOGO_HEIGHT}px;display:inline-block;"></div>'}
        </div>
        <div class="header-right" style="text-align: right;">
            <div class="company-name">ABHYUDYAYA TECHNO SOLUTIONS PRIVATE LIMITED</div>
            <div class="company-details">No.6, Kothari Holdings, Shirur Park Main Road,</div>
            <div class="company-details">Vidyanagar, Hubli, Karnataka, India -580021</div>
            <div class="company-details">GSTIN : 29ABBCA6681J1Z9</div>
            <div class="company-details">Phone: +91 7337820923</div>
            <div class="company-details">Email : info@abhyudyayatech.com | Web : abhyudyayatech.com</div>
        </div>
    </div>
    
    <div class="title">PURCHASE ORDER</div>
    
    <div class="info-container">
        <div class="info-block">
            <strong style="font-size: 11px;">{data.vendor.name}</strong><br>
            {data.vendor.address.replace(chr(10), '<br>')}<br>
            Ph No.: {data.vendor.phone}<br>
            Email: {data.vendor.email}<br>
            GSTIN: {data.vendor.gstin}<br>
            PAN: {data.vendor.pan}
        </div>
        <div class="info-spacer"></div>
        <div class="info-block">
            <strong style="font-size: 10px;">Shipping Address:</strong><br>
            {data.shipping_address.replace(chr(10), '<br>')}
        </div>
    </div>
    
    <div class="po-meta">
        <strong>P.O. Number:</strong> {data.po_number}<br>
        <strong>P.O. Date:</strong> {po_date}
    </div>
    
    <!-- Items Table with Financial Summary INSIDE -->
    <table class="items-table">
        <thead>
        <thead>
            <tr>
                <th style="width: 5%; text-align: center;">SL NO</th>
                <th style="width: 40%; text-align: left;">DESCRIPTION</th>
                <th style="width: 15%; text-align: center;">SKU</th>
                <th style="width: 8%; text-align: center;">QTY</th>
                <th style="width: 15%; text-align: right;">UNIT PRICE RS.</th>
                <th style="width: 17%; text-align: right;">TOTAL PRICE RS.</th>
            </tr>
        </thead>
        <tbody>
            {item_rows}
            
            <!-- Financial Summary Rows INSIDE Table -->
            <tr class="summary-row" style="border-top: 2px solid #000;">
                <td colspan="5" style="text-align: right;">Sub Total</td>
                <td style="text-align: right;">{sub_total:.2f}</td>
            </tr>
            <tr class="summary-row">
                <td colspan="5" style="text-align: right;">GST @ {data.gst_rate}%</td>
                <td style="text-align: right;">{gst_amount:.2f}</td>
            </tr>
            <tr class="grand-total-row">
                <td colspan="5" style="text-align: right;">Grand Total</td>
                <td style="text-align: right;">{grand_total:.2f}</td>
            </tr>
        </tbody>
    </table>
    
    <p class="amount-words"><strong>Amount in Words:</strong> {amount_in_words}</p>
    
    <div class="terms">
        <strong>Terms &amp; Conditions:</strong><br><br>
        1. Please send two copies of your invoice.<br><br>
        2. Enter this order in accordance with the prices, terms, &amp; specifications listed above.<br><br>
        3. Product should be in accordance with the specification mentioned above.<br><br>
        4. Please notify us immediately if you are unable to ship as specified.<br><br>
        5. Transportation, Freight Charges &amp; Packing charges: NIL<br><br>
        6. Installation and commissioning: NIL<br><br>
        7. Payment terms: Against Delivery<br><br>
        8. Delivery: 2 to 3 Days
    </div>
    
    <div class="signature-block">
        <div style="font-weight: bold; font-size: 10px; margin-bottom: 10px;">Authorized Signatory</div>
        <div style="height: 50px; display: flex; align-items: center; justify-content: center; margin: 10px 0;">
            {f'<img class="signature-img" src="{signature_base64}" alt="Signature">' if signature_base64 else ''}
        </div>
        <div style="font-size: 9px; margin-top: 10px;">Abhyudyaya Techno Solutions Private Limited</div>
    </div>
</body>
</html>
"""
    return html


@router.post("/generate")
async def generate_purchase_order(data: PurchaseOrderRequest):
    """Generate PDF using wkhtmltopdf."""
    try:
        html_content = generate_po_html(data)
        
        # Create temp file for PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pdf_file:
            pdf_path = pdf_file.name
        
        # wkhtmltopdf options
        options = {
            'page-size': 'A4',
            'margin-top': '15mm',
            'margin-right': '15mm',
            'margin-bottom': '15mm',
            'margin-left': '15mm',
            'encoding': 'UTF-8',
            'enable-local-file-access': None,
            'print-media-type': None,
        }
        
        # Generate PDF
        pdfkit.from_string(html_content, pdf_path, options=options)
        
        # Read the PDF
        with open(pdf_path, "rb") as f:
            pdf_content = f.read()
        
        # Clean up temp file
        os.unlink(pdf_path)
        
        # Return as downloadable file
        filename = f"PO_{data.po_number.replace('/', '_')}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# PO HISTORY / DRAFT ENDPOINTS
# ============================================================

class POSaveRequest(BaseModel):
    """Request to save a PO as draft or completed."""
    id: Optional[int] = None  # Add ID to track updates
    po_number: str
    po_date: str
    vendor: VendorDetails
    shipping_address: str
    items: List[POItem]
    gst_rate: float = 18.0
    status: str = "draft"  # draft or completed


class POListItem(BaseModel):
    """Response item for PO list."""
    id: int
    po_number: str
    po_date: str
    vendor_name: str
    grand_total: float
    status: str
    created_at: str


@router.post("/save")
async def save_purchase_order(
    data: POSaveRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Save a PO as draft or completed."""
    try:
        # Check for duplicate PO Number
        stmt = select(PurchaseOrder).where(PurchaseOrder.po_number == data.po_number)
        if data.id:
            stmt = stmt.where(PurchaseOrder.id != data.id)
        
        existing_po = session.exec(stmt).first()
        if existing_po:
            raise HTTPException(status_code=400, detail=f"PO Number '{data.po_number}' already exists.")

        # Calculate totals
        sub_total = sum(item.total_price for item in data.items)
        gst_amount = sub_total * (data.gst_rate / 100)
        grand_total = sub_total + gst_amount
        
        if data.id:
            # Update existing PO
            po = session.get(PurchaseOrder, data.id)
            if not po:
                raise HTTPException(status_code=404, detail="PO not found")
            
            # Update fields
            po.po_number = data.po_number
            po.po_date = data.po_date
            po.status = data.status
            po.vendor_name = data.vendor.name
            po.vendor_address = data.vendor.address
            po.vendor_phone = data.vendor.phone
            po.vendor_email = data.vendor.email
            po.vendor_gstin = data.vendor.gstin
            po.vendor_pan = data.vendor.pan
            po.shipping_address = data.shipping_address
            po.items_json = json.dumps([item.dict() for item in data.items])
            po.gst_rate = data.gst_rate
            po.sub_total = sub_total
            po.gst_amount = gst_amount
            po.grand_total = grand_total
            po.updated_at = datetime.utcnow()
            
            session.add(po)
            session.commit()
            session.refresh(po)
            
            return {"id": po.id, "message": f"PO updated as {data.status}"}
            
        else:
            # Create new PO
            po = PurchaseOrder(
                user_id=user.id,
                po_number=data.po_number,
                po_date=data.po_date,
                status=data.status,
                vendor_name=data.vendor.name,
                vendor_address=data.vendor.address,
                vendor_phone=data.vendor.phone,
                vendor_email=data.vendor.email,
                vendor_gstin=data.vendor.gstin,
                vendor_pan=data.vendor.pan,
                shipping_address=data.shipping_address,
                items_json=json.dumps([item.dict() for item in data.items]),
                gst_rate=data.gst_rate,
                sub_total=sub_total,
                gst_amount=gst_amount,
                grand_total=grand_total,
            )
            
            session.add(po)
            session.commit()
            session.refresh(po)
            
            return {"id": po.id, "message": f"PO saved as {data.status}"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_user_purchase_orders(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Get list of user's POs."""
    stmt = select(PurchaseOrder).where(
        PurchaseOrder.user_id == user.id
    ).order_by(PurchaseOrder.created_at.desc())
    
    pos = session.exec(stmt).all()
    
    return [
        POListItem(
            id=po.id,
            po_number=po.po_number,
            po_date=po.po_date,
            vendor_name=po.vendor_name,
            grand_total=po.grand_total,
            status=po.status,
            created_at=po.created_at.isoformat(),
        )
        for po in pos
    ]


@router.get("/list/all")
async def list_all_purchase_orders(
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    """Admin: Get list of all POs."""
    stmt = select(PurchaseOrder).order_by(PurchaseOrder.created_at.desc())
    pos = session.exec(stmt).all()
    
    return [
        {
            "id": po.id,
            "po_number": po.po_number,
            "po_date": po.po_date,
            "vendor_name": po.vendor_name,
            "grand_total": po.grand_total,
            "status": po.status,
            "user_id": po.user_id,
            "created_at": po.created_at.isoformat(),
        }
        for po in pos
    ]


@router.get("/{po_id}")
async def get_purchase_order(
    po_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Get a specific PO."""
    po = session.get(PurchaseOrder, po_id)
    
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    
    # Check permission
    if po.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "id": po.id,
        "po_number": po.po_number,
        "po_date": po.po_date,
        "status": po.status,
        "vendor": {
            "name": po.vendor_name,
            "address": po.vendor_address,
            "phone": po.vendor_phone,
            "email": po.vendor_email,
            "gstin": po.vendor_gstin,
            "pan": po.vendor_pan,
        },
        "shipping_address": po.shipping_address,
        "items": json.loads(po.items_json),
        "gst_rate": po.gst_rate,
        "sub_total": po.sub_total,
        "gst_amount": po.gst_amount,
        "grand_total": po.grand_total,
        "created_at": po.created_at.isoformat(),
    }


@router.delete("/{po_id}")
async def delete_purchase_order(
    po_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Delete a PO."""
    po = session.get(PurchaseOrder, po_id)
    
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    
    # Check permission
    if po.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    session.delete(po)
    session.commit()
    
    return {"message": "PO deleted"}
