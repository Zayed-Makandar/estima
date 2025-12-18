import { useState, useEffect, useRef } from "react";
import { MarketplaceName } from "../types";

const API_BASE = "http://localhost:8000";

interface Recommendation {
  query: string;
  search_count: number;
  has_cached_results: boolean;
}

interface SearchFormProps {
  onSearch: (query: string, marketplaces: MarketplaceName[]) => void;
  query: string;
  setQuery: (q: string) => void;
  compact?: boolean;
  token: string | null;
  selectedMarketplaces: MarketplaceName[];
  setSelectedMarketplaces: (m: MarketplaceName[]) => void;
}

const ALL_MARKETPLACES: { key: MarketplaceName; label: string }[] = [
  { key: "robu", label: "Robu.in" },
  { key: "robocraze", label: "Robocraze" },
  { key: "thinkrobotics", label: "ThinkRobotics" },
  { key: "evelta", label: "Evelta" },
];

export function SearchForm({
  onSearch,
  query,
  setQuery,
  compact = false,
  token,
  selectedMarketplaces,
  setSelectedMarketplaces,
}: SearchFormProps) {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [showRecommendations, setShowRecommendations] = useState(false);
  const [showMarketplaceFilter, setShowMarketplaceFilter] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch recommendations as user types
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (!query || query.length < 2 || !token) {
      setRecommendations([]);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      try {
        const resp = await fetch(
          `${API_BASE}/api/recommendations?q=${encodeURIComponent(query)}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (resp.ok) {
          const data = await resp.json();
          setRecommendations(data);
          setShowRecommendations(data.length > 0);
        }
      } catch (e) {
        console.error("Failed to fetch recommendations:", e);
      }
    }, 300);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [query, token]);

  // Close dropdowns when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowRecommendations(false);
        setShowMarketplaceFilter(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setShowRecommendations(false);
    onSearch(query.trim(), selectedMarketplaces);
  };

  const handleRecommendationClick = (rec: Recommendation) => {
    setQuery(rec.query);
    setShowRecommendations(false);
    onSearch(rec.query, selectedMarketplaces);
  };

  const toggleMarketplace = (key: MarketplaceName) => {
    if (selectedMarketplaces.includes(key)) {
      // Don't allow deselecting all
      if (selectedMarketplaces.length > 1) {
        setSelectedMarketplaces(selectedMarketplaces.filter(m => m !== key));
      }
    } else {
      setSelectedMarketplaces([...selectedMarketplaces, key]);
    }
  };

  const selectedCount = selectedMarketplaces.length;
  const allSelected = selectedCount === ALL_MARKETPLACES.length;

  return (
    <form className={`search-form ${compact ? "compact-search" : ""}`} onSubmit={handleSubmit}>
      {!compact && (
        <div style={{ textAlign: "center", marginBottom: "20px" }}>
          <h2 style={{ color: "var(--color-primary)", margin: "0 0 8px" }}>Search Components</h2>
          <p style={{ color: "var(--color-accent)", fontSize: "0.95rem", margin: 0 }}>Best Rate, No Debate.</p>
        </div>
      )}
      <div className="search-wrapper" ref={searchRef}>
        <div className="search-pill">
          {/* Marketplace Filter Button */}
          <button
            type="button"
            className="marketplace-filter-btn"
            onClick={() => setShowMarketplaceFilter(!showMarketplaceFilter)}
            title="Select marketplaces"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
            </svg>
            {!allSelected && <span className="filter-badge">{selectedCount}</span>}
          </button>

          <input
            className="search-input-field"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => recommendations.length > 0 && setShowRecommendations(true)}
            placeholder="Search components (e.g. Raspberry Pi Pico)..."
            autoComplete="off"
          />
          <button type="submit" className="search-btn-icon" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="5" y1="12" x2="19" y2="12"></line>
              <polyline points="12 5 19 12 12 19"></polyline>
            </svg>
          </button>
        </div>

        {/* Recommendations Dropdown */}
        {showRecommendations && recommendations.length > 0 && (
          <div className="recommendations-dropdown">
            <div className="recommendations-header">Previously Searched</div>
            {recommendations.map((rec, idx) => (
              <button
                key={idx}
                type="button"
                className="recommendation-item"
                onClick={() => handleRecommendationClick(rec)}
              >
                <span className="rec-query">{rec.query}</span>
                {rec.has_cached_results && (
                  <span className="rec-cached" title="Cached - instant results">⚡</span>
                )}
              </button>
            ))}
          </div>
        )}

        {/* Marketplace Filter Dropdown */}
        {showMarketplaceFilter && (
          <div className="marketplace-dropdown">
            <div className="marketplace-header">Search Marketplaces</div>
            {ALL_MARKETPLACES.map(({ key, label }) => (
              <label key={key} className="marketplace-option">
                <input
                  type="checkbox"
                  checked={selectedMarketplaces.includes(key)}
                  onChange={() => toggleMarketplace(key)}
                />
                <span>{label}</span>
              </label>
            ))}
            <div className="marketplace-actions">
              <button
                type="button"
                className="mp-select-all"
                onClick={() => setSelectedMarketplaces(ALL_MARKETPLACES.map(m => m.key))}
              >
                Select All
              </button>
            </div>
          </div>
        )}
      </div>
    </form>
  );
}
