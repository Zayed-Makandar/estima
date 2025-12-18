import React, { useState, useEffect } from "react";
import "../styles.css";

const API_BASE = "http://localhost:8000";

interface POListItem {
    id: number;
    po_number: string;
    po_date: string;
    vendor_name: string;
    grand_total: number;
    status: string;
    created_at: string;
    user_id?: number;
}

interface Props {
    token?: string;
    isAdmin?: boolean;
    onEdit?: (poData: any) => void;
}

const POHistory: React.FC<Props> = ({ token, isAdmin = false, onEdit }) => {
    const [poList, setPoList] = useState<POListItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchPOs = async () => {
        try {
            const endpoint = isAdmin ? "/api/po/list/all" : "/api/po/list";
            const response = await fetch(`${API_BASE}${endpoint}`, {
                headers: {
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
                },
            });

            if (!response.ok) {
                if (response.status === 401) {
                    setPoList([]);
                    return;
                }
                throw new Error('Failed to fetch POs');
            }

            const data = await response.json();
            setPoList(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (token) {
            fetchPOs();
        } else {
            setLoading(false);
        }
    }, [token, isAdmin]);

    const handleDelete = async (id: number) => {
        if (!confirm('Are you sure you want to delete this PO?')) return;

        try {
            const response = await fetch(`${API_BASE}/api/po/${id}`, {
                method: 'DELETE',
                headers: {
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
                },
            });

            if (!response.ok) throw new Error('Failed to delete');

            setPoList(prev => prev.filter(po => po.id !== id));
        } catch (err) {
            alert('Failed to delete PO');
        }
    };

    const handleEdit = async (id: number) => {
        if (!onEdit) return;
        try {
            const response = await fetch(`${API_BASE}/api/po/${id}`, {
                headers: {
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
                },
            });

            if (!response.ok) throw new Error('Failed to fetch details');

            const data = await response.json();
            onEdit(data);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } catch (err) {
            alert('Failed to load draft');
        }
    };

    const handleDownload = async (id: number, poNumber: string) => {
        try {
            // First get the PO details
            const detailResponse = await fetch(`${API_BASE}/api/po/${id}`, {
                headers: {
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
                },
            });

            if (!detailResponse.ok) throw new Error('Failed to get PO details');

            const poData = await detailResponse.json();

            // Then generate PDF
            const pdfResponse = await fetch(`${API_BASE}/api/po/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({
                    po_number: poData.po_number,
                    po_date: poData.po_date,
                    vendor: poData.vendor,
                    shipping_address: poData.shipping_address,
                    items: poData.items,
                    gst_rate: poData.gst_rate,
                }),
            });

            if (!pdfResponse.ok) throw new Error('Failed to generate PDF');

            const blob = await pdfResponse.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `PO_${poNumber.replace(/\//g, '_')}.pdf`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (err) {
            alert('Failed to download PDF');
        }
    };

    if (!token) return null;
    if (loading) return <div className="po-history-section"><p>Loading PO history...</p></div>;
    if (error) return <div className="po-history-section"><p style={{ color: 'red' }}>Error: {error}</p></div>;

    return (
        <div className="po-history-section">
            <div className="po-history-header">
                <h2 style={{ color: "var(--color-primary)", margin: 0 }}>
                    {isAdmin ? 'All Purchase Orders' : 'My Purchase Orders'}
                </h2>
                <button onClick={fetchPOs} className="btn-secondary po-refresh-btn" aria-label="Refresh purchase orders">
                    <span className="po-refresh-icon" aria-hidden="true">↻</span>
                    Refresh
                </button>
            </div>

            {poList.length === 0 ? (
                <div className="po-history-empty">
                    <p>No purchase orders yet.</p>
                </div>
            ) : (
                <div className="po-history-list">
                    {poList.map(po => (
                        <div key={po.id} className="po-history-item">
                            <div className="po-history-info">
                                <span className="po-history-number">{po.po_number}</span>
                                <span className="po-history-vendor">{po.vendor_name}</span>
                            </div>
                            <div className="po-history-meta">
                                <span>₹{po.grand_total.toFixed(2)}</span>
                                <span>{new Date(po.po_date).toLocaleDateString('en-IN')}</span>
                                <span className={`po-status-badge ${po.status}`}>{po.status}</span>
                                {isAdmin && po.user_id && (
                                    <span style={{ color: '#666', fontSize: '0.75rem' }}>User #{po.user_id}</span>
                                )}
                            </div>
                            <div className="po-history-actions">
                                {onEdit && (
                                    <button
                                        onClick={() => handleEdit(po.id)}
                                        className="btn-secondary"
                                    >
                                        Edit
                                    </button>
                                )}
                                <button
                                    onClick={() => handleDownload(po.id, po.po_number)}
                                    className="btn-primary"
                                >
                                    Download
                                </button>
                                <button
                                    onClick={() => handleDelete(po.id)}
                                    className="btn-remove-sm"
                                    style={{ padding: '6px 10px' }}
                                >
                                    ✕
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default POHistory;
