import { useState, useEffect } from "react";
import { MarketplaceItem, MarketplaceName } from "../types";

type Props = {
  items: MarketplaceItem[];
  note: string | null;
  hasSearched: boolean;
  onAdd: (item: MarketplaceItem) => void;
  onRemove: (item: MarketplaceItem) => void;
  chosenItemIds: Set<string>;
  onImageClick: (src: string, title: string) => void;
  isFromCache?: boolean;
  onRefreshItem?: (item: MarketplaceItem) => Promise<MarketplaceItem | null>;
  sourceFilter?: MarketplaceName | null;
  onSourceFilterChange?: (source: MarketplaceName | null) => void;
  allResults?: MarketplaceItem[];
};

const SOURCE_LABELS: Record<MarketplaceName, string> = {
  robu: "Robu.in",
  robocraze: "Robocraze",
  thinkrobotics: "ThinkRobotics",
  evelta: "Evelta",
  Draft: "Draft PO",
};

export function ResultsTable({
  items,
  note,
  hasSearched,
  onAdd,
  onRemove,
  chosenItemIds,
  onImageClick,
  isFromCache = false,
  onRefreshItem,
  sourceFilter,
  onSourceFilterChange,
  allResults = [],
}: Props) {
  const [sortAsc, setSortAsc] = useState(true);
  const [refreshingUrls, setRefreshingUrls] = useState<Set<string>>(new Set());
  const [localItems, setLocalItems] = useState<MarketplaceItem[]>(items);
  const [showSourceDropdown, setShowSourceDropdown] = useState(false);

  // Sync localItems with items prop when items change
  useEffect(() => {
    setLocalItems(items);
  }, [items]);

  const emptyMessage = note || (hasSearched ? "No results found." : "No results yet.");

  // Helper to extract numeric price
  const getPriceVal = (p: string) => {
    if (!p) return Infinity;
    const clean = p.replace(/[^0-9.]/g, '');
    const val = parseFloat(clean);
    return isNaN(val) ? Infinity : val;
  };

  // Sort logic
  const sortedItems = [...localItems].sort((a, b) => {
    const pa = getPriceVal(a.price_text);
    const pb = getPriceVal(b.price_text);
    return sortAsc ? pa - pb : pb - pa;
  });

  // Helper to format price cell - removes (Incl. GST) note
  const formatPriceDisplay = (text: string) => {
    // Remove any parenthetical notes like (Incl. GST)
    const mainPrice = text.replace(/\(.*?\)/g, "").trim();

    return (
      <div className="price-cell">
        <span className="price-val">{mainPrice}</span>
      </div>
    );
  };

  const handleRefresh = async (item: MarketplaceItem) => {
    if (!onRefreshItem) return;

    setRefreshingUrls(prev => new Set(prev).add(item.url));

    const refreshed = await onRefreshItem(item);

    if (refreshed) {
      setLocalItems(prev => prev.map(i =>
        i.url === item.url ? refreshed : i
      ));
    }

    setRefreshingUrls(prev => {
      const next = new Set(prev);
      next.delete(item.url);
      return next;
    });
  };

  // Get unique sources from all results for filter dropdown
  const availableSources = [...new Set(allResults.map(item => item.source))];

  const handleSourceClick = (source: MarketplaceName) => {
    if (onSourceFilterChange) {
      if (sourceFilter === source) {
        onSourceFilterChange(null); // Clear filter
      } else {
        onSourceFilterChange(source);
      }
    }
    setShowSourceDropdown(false);
  };

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h2 style={{ color: "var(--color-primary)", margin: 0 }} className="results-title">Results</h2>
        {sourceFilter && (
          <button
            className="source-filter-active"
            onClick={() => onSourceFilterChange && onSourceFilterChange(null)}
          >
            Showing: {SOURCE_LABELS[sourceFilter]} ✕
          </button>
        )}
      </div>
      {items.length === 0 ? (
        <p className="muted" style={{ textAlign: "center", padding: "20px" }}>{emptyMessage}</p>
      ) : (
        <div className="table-scroll-container">
          <table className="results-table">
            <thead>
              <tr>
                <th>Image</th>
                <th>Title</th>
                <th onClick={() => setSortAsc(!sortAsc)} className="sortable-header">
                  Price {sortAsc ? "↑" : "↓"}
                </th>
                <th>Availability</th>
                <th style={{ position: "relative" }}>
                  <button
                    className="source-header-btn"
                    onClick={() => setShowSourceDropdown(!showSourceDropdown)}
                    style={{ background: 'none', border: 'none', color: 'white', fontWeight: 600, cursor: 'pointer', padding: 0 }}
                  >
                    Source ▼
                  </button>
                  {showSourceDropdown && (
                    <div className="source-dropdown" style={{
                      position: "absolute",
                      top: "100%",
                      right: 0,
                      background: "white",
                      border: "1px solid #ddd",
                      borderRadius: "8px",
                      boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                      zIndex: 20,
                      minWidth: "150px",
                      display: "flex",
                      flexDirection: "column",
                      overflow: "hidden"
                    }}>
                      <button
                        className={`source-dropdown-item ${!sourceFilter ? 'active' : ''}`}
                        onClick={() => { onSourceFilterChange && onSourceFilterChange(null); setShowSourceDropdown(false); }}
                        style={{ padding: "10px", textAlign: "left", background: !sourceFilter ? "#f0f0f0" : "white", border: "none", cursor: "pointer", color: "var(--color-secondary)" }}
                      >
                        All Sources
                      </button>
                      {availableSources.map(source => (
                        <button
                          key={source}
                          className={`source-dropdown-item ${sourceFilter === source ? 'active' : ''}`}
                          onClick={() => handleSourceClick(source)}
                          style={{ padding: "10px", textAlign: "left", background: sourceFilter === source ? "#f0f0f0" : "white", border: "none", cursor: "pointer", color: "var(--color-secondary)" }}
                        >
                          {SOURCE_LABELS[source]}
                        </button>
                      ))}
                    </div>
                  )}
                </th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {sortedItems.map((item) => {
                const isChosen = chosenItemIds.has(item.url);
                const isRefreshing = refreshingUrls.has(item.url);
                return (
                  <tr key={item.url} className={isChosen ? "chosen-row" : ""}>
                    <td>
                      <img
                        src={item.image_url}
                        alt={item.title}
                        className="product-thumb"
                        onClick={() => onImageClick(item.image_url, item.title)}
                        style={{ cursor: "zoom-in" }}
                      />
                    </td>
                    <td>
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                        className="item-link"
                      >
                        {item.title}
                      </a>
                    </td>
                    <td className="price-col">
                      {formatPriceDisplay(item.price_text)}
                    </td>
                    <td>
                      <span
                        className={`availability-tag ${item.availability === "In Stock" ? "in-stock" : "out-of-stock"
                          }`}
                      >
                        {item.availability}
                      </span>
                    </td>
                    <td>{SOURCE_LABELS[item.source] || item.source}</td>
                    <td>
                      {/* Action Buttons */}
                      <div style={{ display: 'flex', gap: '5px' }}>
                        <button
                          className={isChosen ? "btn-remove" : "btn-add"}
                          onClick={() => isChosen ? onRemove(item) : onAdd(item)}
                          title={isChosen ? "Click to remove" : "Click to add"}
                        >
                          {isChosen ? "Added" : "Add"}
                        </button>

                        {/* Refresh Button for Cached/Old Items */}
                        {(isFromCache || item.source === 'Draft') && onRefreshItem && (
                          <button
                            className="btn-refresh"
                            onClick={() => handleRefresh(item)}
                            disabled={isRefreshing}
                            title="Refresh latest price/stock"
                          >
                            {isRefreshing ? "..." : "↻"}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
