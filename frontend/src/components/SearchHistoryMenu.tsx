import { useState, useRef, useEffect } from "react";
import { SearchHistoryItem } from "../types";

interface SearchHistoryMenuProps {
    history: SearchHistoryItem[];
    onSelect: (item: SearchHistoryItem) => void;
}

export function SearchHistoryMenu({ history, onSelect }: SearchHistoryMenuProps) {
    const [isOpen, setIsOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);

    // Close menu when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);

    if (history.length === 0) return null;

    const formatTime = (item: SearchHistoryItem) => {
        if (item.searched_at) {
            return new Date(item.searched_at).toLocaleString([], {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
        if (item.timestamp) {
            return new Date(item.timestamp).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
            });
        }
        return "";
    };

    return (
        <div className="history-menu-container" ref={menuRef} style={{ position: "relative" }}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="btn-history"
                style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
            >
                <span>History</span>
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M6 9l6 6 6-6" />
                </svg>
            </button>

            {isOpen && (
                <div className="history-dropdown" style={{
                    position: "absolute",
                    top: "120%",
                    right: 0,
                    width: "280px",
                    padding: "0",
                    zIndex: 2000,
                    maxHeight: "350px",
                    overflowY: "auto",
                    backgroundColor: "var(--color-secondary)",
                    borderRadius: "8px",
                    boxShadow: "0 4px 20px rgba(0, 0, 0, 0.3)",
                }}>
                    <div style={{
                        padding: "12px 16px",
                        borderBottom: "1px solid rgba(255,255,255,0.1)",
                        fontSize: "0.85rem",
                        color: "rgba(255,255,255,0.7)",
                        fontWeight: 600,
                    }}>
                        Recent Searches
                    </div>
                    {history.slice(0, 15).map((item) => (
                        <button
                            key={item.id}
                            onClick={() => {
                                onSelect(item);
                                setIsOpen(false);
                            }}
                            className="history-item-btn"
                        >
                            <div style={{ fontWeight: 600, color: "#fff" }}>{item.query}</div>
                            <div style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.5)", marginTop: "2px" }}>
                                {item.items_count ?? item.items?.length ?? 0} results • {formatTime(item)}
                            </div>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
