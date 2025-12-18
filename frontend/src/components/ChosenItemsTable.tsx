import React, { useState, useEffect } from "react";
import * as XLSX from "xlsx-js-style";
import { MarketplaceItem } from "../types";
import "../styles.css";

const API_BASE = "http://localhost:8000";

interface Props {
    items: MarketplaceItem[];
    onRemove: (index: number) => void;
    token?: string;
    draftData?: any; // The full PO object from backend
}

// Helper to parse price from price_text
const parsePrice = (priceText: string): number => {
    const cleaned = priceText.replace(/\(.*?\)/g, "").replace(/[^0-9.]/g, "");
    const val = parseFloat(cleaned);
    return isNaN(val) ? 0 : val;
};

const ChosenItemsTable: React.FC<Props> = ({ items, onRemove, token, draftData }) => {
    // State
    const [quantities, setQuantities] = useState<Record<string, number>>({});
    const [descriptions, setDescriptions] = useState<Record<string, string>>({});
    const [skus, setSkus] = useState<Record<string, string>>({});
    const [customPrices, setCustomPrices] = useState<Record<string, number>>({});

    const [gstRate, setGstRate] = useState<number>(18);
    const [showPOModal, setShowPOModal] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

    // PO Form state
    const [poForm, setPoForm] = useState({
        vendorName: "",
        vendorAddress: "",
        vendorPhone: "",
        vendorEmail: "",
        vendorGstin: "",
        vendorPan: "",
        poNumber: "",
        poDate: new Date().toISOString().split('T')[0],
        shippingAddress: `ABHYUDYAYA TECHNO SOLUTIONS PRIVATE LIMITED
#6, Kothari Holdings, Shirur Park Main Road,
Opp Sukruti Collage, Vidyanagar Hubli,
Hubli, 580021 Karnataka, KA, India
info@abhyudyayatech.com`,
    });

    // Handle initial draft data loading
    useEffect(() => {
        if (draftData) {
            setPoForm({
                vendorName: draftData.vendor.name || "",
                vendorAddress: draftData.vendor.address || "",
                vendorPhone: draftData.vendor.phone || "",
                vendorEmail: draftData.vendor.email || "",
                vendorGstin: draftData.vendor.gstin || "",
                vendorPan: draftData.vendor.pan || "",
                poNumber: draftData.po_number || "",
                poDate: draftData.po_date || new Date().toISOString().split('T')[0],
                shippingAddress: draftData.shipping_address || poForm.shippingAddress,
            });
            setGstRate(draftData.gst_rate || 18);

            // Populate quantities, descriptions, skus, prices
            const newQuantities: Record<string, number> = {};
            const newDescriptions: Record<string, string> = {};
            const newSkus: Record<string, string> = {};
            const newPrices: Record<string, number> = {};

            items.forEach((item, index) => {
                const draftItem = draftData.items[index];
                if (draftItem) {
                    newQuantities[item.url] = draftItem.quantity;
                    newDescriptions[item.url] = draftItem.description;
                    newSkus[item.url] = draftItem.sku || "";
                    newPrices[item.url] = draftItem.unit_price;
                }
            });

            setQuantities(newQuantities);
            setDescriptions(newDescriptions);
            setSkus(newSkus);
            setCustomPrices(newPrices);
        }
    }, [draftData, items]);

    // Initialize item states
    useEffect(() => {
        const newDescriptions: Record<string, string> = {};
        const newSkus: Record<string, string> = {};
        const newPrices: Record<string, number> = {};

        items.forEach(item => {
            // Keep existing values or init new
            if (!descriptions[item.url]) {
                newDescriptions[item.url] = item.title;
            }
            if (skus[item.url] === undefined) {
                newSkus[item.url] = item.sku || "";
            }
            if (customPrices[item.url] === undefined) {
                // Default price logic: Scraped Price / 1.18 (Base Price)
                const scrapedPrice = parsePrice(item.price_text);
                newPrices[item.url] = parseFloat((scrapedPrice / 1.18).toFixed(2));
            }
        });

        if (Object.keys(newDescriptions).length > 0) {
            setDescriptions(prev => ({ ...prev, ...newDescriptions }));
        }
        if (Object.keys(newSkus).length > 0) {
            setSkus(prev => ({ ...prev, ...newSkus }));
        }
        if (Object.keys(newPrices).length > 0) {
            setCustomPrices(prev => ({ ...prev, ...newPrices }));
        }
    }, [items]);

    const getQuantity = (url: string) => quantities[url] || 1;
    const getDescription = (url: string, title: string) => descriptions[url] || title;
    const getSku = (url: string) => skus[url] || "";
    const getUnitPrice = (url: string) => customPrices[url] || 0;

    const setQuantity = (url: string, qty: number) => {
        setQuantities(prev => ({ ...prev, [url]: Math.max(1, qty) }));
    };

    const setDescription = (url: string, desc: string) => {
        setDescriptions(prev => ({ ...prev, [url]: desc }));
    };

    const setSku = (url: string, sku: string) => {
        setSkus(prev => ({ ...prev, [url]: sku.toUpperCase() }));
    };

    const setUnitPrice = (url: string, price: number) => {
        setCustomPrices(prev => ({ ...prev, [url]: Math.max(0, price) }));
    };

    // Calculate items with all details
    const itemsWithCalc = items.map((item, index) => {
        const qty = getQuantity(item.url);
        const unitPrice = getUnitPrice(item.url); // Base Price
        const totalPrice = unitPrice * qty;
        const description = getDescription(item.url, item.title);
        const sku = getSku(item.url);
        return { item, index, qty, unitPrice, totalPrice, description, sku };
    });

    // Financial summary
    const subTotal = itemsWithCalc.reduce((sum, i) => sum + i.totalPrice, 0);
    const gstAmount = subTotal * (gstRate / 100);
    const grandTotal = subTotal + gstAmount;

    // Form validation
    const isFormValid =
        poForm.vendorName.trim() !== "" &&
        poForm.vendorAddress.trim() !== "" &&
        poForm.poNumber.trim() !== "" &&
        poForm.poDate.trim() !== "" &&
        itemsWithCalc.every(i => i.description.trim() !== "");

    const getPOData = () => ({
        id: draftData?.id,
        po_number: poForm.poNumber,
        po_date: poForm.poDate,
        vendor: {
            name: poForm.vendorName,
            address: poForm.vendorAddress,
            phone: poForm.vendorPhone,
            email: poForm.vendorEmail,
            gstin: poForm.vendorGstin,
            pan: poForm.vendorPan,
        },
        shipping_address: poForm.shippingAddress,
        items: itemsWithCalc.map(({ description, sku, qty, unitPrice, totalPrice }, idx) => ({
            sl_no: idx + 1,
            description,
            sku,
            quantity: qty,
            unit_price: unitPrice,
            total_price: totalPrice,
        })),
        gst_rate: gstRate,
    });

    // Generate Quotation Excel
    const handleGenerateQuotation = () => {
        const wb = XLSX.utils.book_new();

        const wsData: any[][] = [
            ["ABHYUDYAYA TECHNO SOLUTIONS - (OPC) PRIVATE LIMITED"],
            ["No.6, Kothari Holdings, Shirur Park Main Road, Vidyanagar, Hubli, Karnataka, India -580021"],
            [""], // Spacer
            ["Sl no", "Description", "SKU", "QTY"]
        ];

        itemsWithCalc.forEach((i, idx) => {
            wsData.push([idx + 1, i.description, i.sku, i.qty]);
        });

        const ws = XLSX.utils.aoa_to_sheet(wsData as any[]);

        // Merge Company Name (Row 0) and Address (Row 1) across 4 columns
        if (!ws['!merges']) ws['!merges'] = [];
        ws['!merges'].push({ s: { r: 0, c: 0 }, e: { r: 0, c: 3 } }); // Company Name
        ws['!merges'].push({ s: { r: 1, c: 0 }, e: { r: 1, c: 3 } }); // Address

        XLSX.utils.book_append_sheet(wb, ws, "Quotation");
        XLSX.writeFile(wb, `quotation_${Date.now()}.xlsx`);
    };

    // Estimate Excel
    const handleEstimate = () => {
        const wb = XLSX.utils.book_new();

        const wsData: any[][] = [
            ["ESTIMATE"],
            [""],
            ["Sl No", "Quantity", "Unit Price (Base)", "Total Price (Base)"]
        ];

        itemsWithCalc.forEach((i, idx) => {
            wsData.push([
                idx + 1,
                i.qty,
                parseFloat(i.unitPrice.toFixed(2)),
                parseFloat(i.totalPrice.toFixed(2))
            ]);
        });

        wsData.push(["", "", "", ""]);
        wsData.push(["", "", "Sub Total", parseFloat(subTotal.toFixed(2))]);
        wsData.push(["", "", `GST @ ${gstRate}%`, parseFloat(gstAmount.toFixed(2))]);
        wsData.push(["", "", "Grand Total", parseFloat(grandTotal.toFixed(2))]);

        const ws = XLSX.utils.aoa_to_sheet(wsData as any[]);
        XLSX.utils.book_append_sheet(wb, ws, "Estimate");
        XLSX.writeFile(wb, `estimation_${Date.now()}.xlsx`);
    };

    const handleExportCSV = () => {
        const lines: string[] = [];
        lines.push("ABHYUDYAYA TECHNO SOLUTIONS PRIVATE LIMITED");
        lines.push("\"No.6, Kothari Holdings, Shirur Park Main Road, Vidyanagar, Hubli, Karnataka, India -580021\"");
        lines.push("GSTIN: 29ABBCA6681J1Z9 | Phone: +91 7337820923 | Email: info@abhyudyayatech.com");
        lines.push("");
        lines.push("PURCHASE ORDER");
        lines.push("");
        lines.push(`P.O. Number,${poForm.poNumber}`);
        lines.push(`P.O. Date,${poForm.poDate}`);
        lines.push("");
        lines.push("VENDOR DETAILS");
        lines.push(`Name,\"${poForm.vendorName}\"`);
        lines.push(`Address,\"${poForm.vendorAddress.replace(/\n/g, ' ')}\"`);
        lines.push(`Phone,${poForm.vendorPhone}`);
        lines.push(`Email,${poForm.vendorEmail}`);
        lines.push(`GSTIN,${poForm.vendorGstin}`);
        lines.push(`PAN,${poForm.vendorPan}`);
        lines.push("");
        lines.push("SHIPPING ADDRESS");
        lines.push(`\"${poForm.shippingAddress.replace(/\n/g, ' ')}\"`);
        lines.push("");
        lines.push("SL NO,DESCRIPTION,SKU,QTY,UNIT PRICE,TOTAL PRICE");
        itemsWithCalc.forEach(({ description, sku, qty, unitPrice, totalPrice }, idx) => {
            lines.push(`${idx + 1},"${description.replace(/"/g, '""')}",${sku},${qty},${unitPrice.toFixed(2)},${totalPrice.toFixed(2)}`);
        });
        lines.push("");
        lines.push(`"","","","","Sub Total",${subTotal.toFixed(2)}`);
        lines.push(`"","","","","GST @ ${gstRate}%",${gstAmount.toFixed(2)}`);
        lines.push(`"","","","","Grand Total",${grandTotal.toFixed(2)}`);
        lines.push("");
        lines.push("TERMS & CONDITIONS");
        lines.push("1. Please send two copies of your invoice.");
        lines.push("2. Enter this order in accordance with the prices terms and specifications listed above.");
        lines.push("3. Product should be in accordance with the specification mentioned above.");
        lines.push("4. Please notify us immediately if you are unable to ship as specified.");
        lines.push("5. Transportation Freight Charges and Packing charges: NIL");
        lines.push("6. Installation and commissioning: NIL");
        lines.push("7. Payment terms: Against Delivery");
        lines.push("8. Delivery: 2 to 3 Days");

        const csv = lines.join("\n");
        const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `PO_${poForm.poNumber.replace(/\//g, '_') || 'draft'}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
    };

    const handleSaveDraft = async () => {
        setIsSaving(true);
        try {
            const response = await fetch(`${API_BASE}/api/po/save`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({ ...getPOData(), status: 'draft' }),
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to save draft');
            }

            alert('PO saved as draft! You can access it from the PO History section.');
        } catch (error) {
            alert(`Failed to save draft: ${error instanceof Error ? error.message : 'Unknown error'}`);
        } finally {
            setIsSaving(false);
        }
    };

    const generatePDF = async () => {
        if (!isFormValid) {
            alert('Please fill in all required fields and ensure all descriptions are not empty.');
            return;
        }

        setIsGenerating(true);

        try {
            // Save as completed first
            const saveResponse = await fetch(`${API_BASE}/api/po/save`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({ ...getPOData(), status: 'completed' }),
            });
            if (!saveResponse.ok) {
                const err = await saveResponse.json();
                throw new Error(err.detail || 'Failed to save PO record');
            }

            // Generate PDF
            const response = await fetch(`${API_BASE}/api/po/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
                },
                body: JSON.stringify(getPOData()),
            });

            if (!response.ok) throw new Error('Failed to generate PDF');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `PO_${poForm.poNumber.replace(/\//g, '_')}.pdf`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);

            setShowPOModal(false);
        } catch (error) {
            alert(`Failed to generate PDF: ${error instanceof Error ? error.message : 'Unknown error'}`);
        } finally {
            setIsGenerating(false);
        }
    };

    if (items.length === 0) return null;

    return (
        <div className="chosen-items-section">
            <div className="chosen-items-header">
                <h2 style={{ color: "var(--color-primary)", margin: 0 }}>Chosen Items</h2>
                <div className="gst-input-group">
                    <label>GST @ </label>
                    <input
                        type="number"
                        value={gstRate}
                        onChange={(e) => setGstRate(Math.max(0, parseFloat(e.target.value) || 0))}
                        min="0"
                        max="100"
                        step="0.5"
                        className="gst-input"
                    />
                    <span>%</span>
                </div>
            </div>

            <div className="table-scroll-container">
                <table className="chosen-items-table">
                    <thead>
                        <tr>
                            <th style={{ width: "50px" }} className="center">Sl&nbsp;No</th>
                            <th>Description</th>
                            <th style={{ width: "100px" }} className="center">SKU</th>
                            <th style={{ width: "120px" }} className="center">Quantity</th>
                            <th style={{ width: "120px" }} className="right">Unit Price</th>
                            <th style={{ width: "120px" }} className="right">Total Price</th>
                            <th style={{ width: "110px" }} className="center">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {itemsWithCalc.map(({ item, index, qty, unitPrice, totalPrice, description, sku }, idx) => (
                            <tr key={item.url}>
                                <td className="center">{idx + 1}</td>
                                <td className="description-cell">
                                    <input
                                        type="text"
                                        value={description}
                                        onChange={(e) => setDescription(item.url, e.target.value)}
                                        className={`description-input ${!description.trim() ? 'error' : ''}`}
                                        placeholder="Description"
                                    />
                                </td>
                                <td>
                                    <input
                                        type="text"
                                        value={sku}
                                        onChange={(e) => setSku(item.url, e.target.value)}
                                        className="sku-input"
                                        placeholder="SKU"
                                        style={{ width: "100%", padding: "4px", border: "1px solid #ddd" }}
                                    />
                                </td>
                                <td>
                                    <div className="qty-controls">
                                        <button className="qty-btn" onClick={() => setQuantity(item.url, qty - 1)}>−</button>
                                        <input
                                            type="number"
                                            value={qty}
                                            onChange={(e) => setQuantity(item.url, parseInt(e.target.value) || 1)}
                                            min="1"
                                            className="qty-input"
                                        />
                                        <button className="qty-btn" onClick={() => setQuantity(item.url, qty + 1)}>+</button>
                                    </div>
                                </td>
                                <td className="right">
                                    <input
                                        type="number"
                                        value={unitPrice}
                                        onChange={(e) => setUnitPrice(item.url, parseFloat(e.target.value))}
                                        className="price-input"
                                        min="0"
                                        step="0.01"
                                        style={{ width: "100%", padding: "4px", border: "1px solid #ddd", textAlign: "right" }}
                                    />
                                </td>
                                <td className="right bold">₹{totalPrice.toFixed(2)}</td>
                                <td className="center">
                                    <div className="chosen-action-buttons">
                                        <a href={item.url} target="_blank" rel="noopener noreferrer" className="btn-view">
                                            View
                                        </a>
                                        <button onClick={() => onRemove(index)} className="btn-remove-sm">✕</button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="financial-summary-section">
                <div className="summary-row">
                    <span>Sub Total</span>
                    <span>₹{subTotal.toFixed(2)}</span>
                </div>
                <div className="summary-row">
                    <span>GST @ {gstRate}%</span>
                    <span>₹{gstAmount.toFixed(2)}</span>
                </div>
                <div className="summary-row grand-total-row">
                    <span>Grand Total</span>
                    <span>₹{grandTotal.toFixed(2)}</span>
                </div>
            </div>

            <div className="chosen-items-actions">
                <button onClick={handleGenerateQuotation} className="btn-secondary" style={{ backgroundColor: '#2e7d32', borderColor: '#2e7d32', color: 'white' }}>Generate Quotation</button>
                <button onClick={handleEstimate} className="btn-secondary" style={{ backgroundColor: '#0277bd', borderColor: '#0277bd', color: 'white' }}>Estimate</button>
                <button onClick={() => setShowPOModal(true)} className="btn-primary">Generate Purchase Order</button>
            </div>

            {/* PO Modal */}
            {showPOModal && (
                <div className="po-modal-backdrop" onClick={() => setShowPOModal(false)}>
                    <div className="po-modal" onClick={(e) => e.stopPropagation()}>
                        <div className="po-modal-header">
                            <h3>Purchase Order Details</h3>
                            <button className="po-close-btn" onClick={() => setShowPOModal(false)}>×</button>
                        </div>
                        <div className="po-modal-body">
                            <div className="po-form-section">
                                <h4>Vendor Details <span className="required-note">* Required</span></h4>
                                <div className="po-form-row">
                                    <div className="po-form-group">
                                        <label>Vendor/Company Name *</label>
                                        <input
                                            type="text"
                                            value={poForm.vendorName}
                                            onChange={(e) => setPoForm({ ...poForm, vendorName: e.target.value })}
                                            placeholder="e.g. TIF LABS PVT LTD"
                                            className={!poForm.vendorName.trim() ? 'invalid' : ''}
                                        />
                                    </div>
                                </div>
                                <div className="po-form-row">
                                    <div className="po-form-group">
                                        <label>Address *</label>
                                        <textarea
                                            value={poForm.vendorAddress}
                                            onChange={(e) => setPoForm({ ...poForm, vendorAddress: e.target.value })}
                                            placeholder="Full address"
                                            rows={3}
                                            className={!poForm.vendorAddress.trim() ? 'invalid' : ''}
                                        />
                                    </div>
                                </div>
                                <div className="po-form-row two-col">
                                    <div className="po-form-group"><label>Phone</label><input type="text" value={poForm.vendorPhone} onChange={(e) => setPoForm({ ...poForm, vendorPhone: e.target.value })} /></div>
                                    <div className="po-form-group"><label>Email</label><input type="email" value={poForm.vendorEmail} onChange={(e) => setPoForm({ ...poForm, vendorEmail: e.target.value })} /></div>
                                </div>
                                <div className="po-form-row two-col">
                                    <div className="po-form-group"><label>GSTIN</label><input type="text" value={poForm.vendorGstin} onChange={(e) => setPoForm({ ...poForm, vendorGstin: e.target.value })} /></div>
                                    <div className="po-form-group"><label>PAN</label><input type="text" value={poForm.vendorPan} onChange={(e) => setPoForm({ ...poForm, vendorPan: e.target.value })} /></div>
                                </div>
                            </div>
                            <div className="po-form-section">
                                <h4>PO Information</h4>
                                <div className="po-form-row two-col">
                                    <div className="po-form-group"><label>P.O. Number *</label><input type="text" value={poForm.poNumber} onChange={(e) => setPoForm({ ...poForm, poNumber: e.target.value })} placeholder="ATS/24-25/XX" className={!poForm.poNumber.trim() ? 'invalid' : ''} /></div>
                                    <div className="po-form-group"><label>P.O. Date *</label><input type="date" value={poForm.poDate} onChange={(e) => setPoForm({ ...poForm, poDate: e.target.value })} className={!poForm.poDate.trim() ? 'invalid' : ''} /></div>
                                </div>
                            </div>
                            <div className="po-form-section">
                                <h4>Shipping Address</h4>
                                <div className="po-form-row">
                                    <div className="po-form-group"><textarea value={poForm.shippingAddress} onChange={(e) => setPoForm({ ...poForm, shippingAddress: e.target.value })} rows={5} /></div>
                                </div>
                            </div>
                            <div className="po-summary-preview">
                                <h4>Order Summary</h4>
                                <p><strong>{items.length}</strong> items | Sub Total: <strong>₹{subTotal.toFixed(2)}</strong> | GST: <strong>₹{gstAmount.toFixed(2)}</strong> | Grand Total: <strong>₹{grandTotal.toFixed(2)}</strong></p>
                                {!isFormValid && <p className="validation-warning">⚠️ Please fill in all required fields</p>}
                            </div>
                        </div>
                        <div className="po-modal-footer">
                            <button className="btn-secondary" onClick={() => setShowPOModal(false)}>Cancel</button>
                            <button className="btn-draft" onClick={handleSaveDraft} disabled={isSaving}>{isSaving ? 'Saving...' : 'Save as Draft'}</button>
                            <button className="btn-export" onClick={handleExportCSV}>Export CSV</button>
                            <button className="btn-primary" onClick={generatePDF} disabled={!isFormValid || isGenerating} title={!isFormValid ? 'Fill required fields' : 'Download PDF'}>{isGenerating ? 'Generating...' : 'Download PDF'}</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ChosenItemsTable;
