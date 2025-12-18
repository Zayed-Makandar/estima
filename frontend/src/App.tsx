import { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Login } from "./components/Login";
import { SearchForm } from "./components/SearchForm";
import { ResultsTable } from "./components/ResultsTable";
import ChosenItemsTable from "./components/ChosenItemsTable";
import POHistory from "./components/POHistory";
import LoadingSpinner from "./components/LoadingSpinner";
import { SearchHistoryMenu } from "./components/SearchHistoryMenu";
import { ImageMagnifier } from "./components/ImageMagnifier";
import { AdminDashboard } from "./components/AdminDashboard";
import { MarketplaceItem, MarketplaceName, SearchHistoryItem, SearchResponse } from "./types";
import "./styles.css";

const API_BASE = "http://localhost:8000";

const ALL_MARKETPLACES: MarketplaceName[] = ["robu", "robocraze", "thinkrobotics", "evelta"];

function MainApp() {
  const { user, token, logout, isAdmin, isAuthenticated, loading: authLoading } = useAuth();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MarketplaceItem[]>([]);
  const [chosenItems, setChosenItems] = useState<MarketplaceItem[]>([]);
  const chosenItemIds = new Set(chosenItems.map((i) => i.url));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [lightbox, setLightbox] = useState<{ src: string; title: string } | null>(null);
  const [history, setHistory] = useState<SearchHistoryItem[]>([]);
  const [isFromCache, setIsFromCache] = useState(false);
  const [showAdminDashboard, setShowAdminDashboard] = useState(false);
  const [selectedMarketplaces, setSelectedMarketplaces] = useState<MarketplaceName[]>(ALL_MARKETPLACES);
  const [sourceFilter, setSourceFilter] = useState<MarketplaceName | null>(null);
  const [activeDraft, setActiveDraft] = useState<any>(null); // State for loaded draft data

  // Fetch search history from API on mount
  useEffect(() => {
    if (isAuthenticated && token) {
      fetchHistory();
    }
  }, [isAuthenticated, token]);

  // ... (fetchHistory, handleSearch, etc. remain the same) ...

  const handleEditDraft = (draft: any) => {
    // Convert draft items back to MarketplaceItem format for displaying in ChosenItemsTable
    const items = draft.items.map((item: any, idx: number) => ({
      title: item.description,
      price_text: `₹${item.unit_price}`,
      url: `draft-${draft.id}-${idx}`, // Unique key for draft items
      availability: 'In Stock',
      source: 'Draft',
      image_url: '', // Image URL not preserved in PO draft
    }));

    setChosenItems(items);
    setActiveDraft(draft);

    // Scroll to chosen items table
    const table = document.querySelector('.chosen-items-section');
    if (table) {
      table.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleGoToPOSection = () => {
    const el = document.querySelector(".po-history-section");
    if (el) {
      (el as HTMLElement).scrollIntoView({ behavior: "smooth" });
    }
  };

  const fetchHistory = async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/history`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (resp.ok) {
        const data = await resp.json();
        setHistory(data.map((h: any) => ({
          id: h.id,
          query: h.query,
          items: [],
          items_count: h.items_count,
          note: h.note,
          searched_at: h.searched_at,
        })));
      }
    } catch (e) {
      console.error("Failed to fetch history:", e);
    }
  };

  const handleSearch = async (searchQuery: string, marketplaces: MarketplaceName[]) => {
    setHasSearched(true);
    setLoading(true);
    setError(null);
    setNote(null);
    setSourceFilter(null);
    try {
      const resp = await fetch(`${API_BASE}/api/marketplaces/search_all`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          query: searchQuery,
          limit: 6,
          marketplaces: marketplaces.length === ALL_MARKETPLACES.length ? null : marketplaces,
        }),
      });
      if (!resp.ok) {
        throw new Error(`Request failed (${resp.status})`);
      }
      const data: SearchResponse = await resp.json();
      setResults(data.items);
      setNote(data.note || null);
      setIsFromCache(data.from_cache);

      // Refresh history after search
      fetchHistory();

    } catch (err: any) {
      setError(err.message || "Search failed");
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleHistorySelect = async (item: SearchHistoryItem) => {
    // Fetch full history details
    try {
      const resp = await fetch(`${API_BASE}/api/history/${item.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (resp.ok) {
        const data = await resp.json();
        setQuery(data.query);
        setResults(data.items);
        setNote(data.note);
        setError(null);
        setHasSearched(true);
        setIsFromCache(true);
        setSourceFilter(null);
      }
    } catch (e) {
      console.error("Failed to fetch history details:", e);
    }
  };

  const handleGoHome = () => {
    setHasSearched(false);
    setResults([]);
    setNote(null);
    setError(null);
    setSourceFilter(null);
    setIsFromCache(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleAdd = (item: MarketplaceItem) => {
    setChosenItems((prev) => [...prev, item]);
  };

  const handleRemove = (index: number) => {
    setChosenItems((prev) => prev.filter((_, i) => i !== index));
  };

  const handleRemoveByItem = (item: MarketplaceItem) => {
    setChosenItems((prev) => prev.filter((i) => i.url !== item.url));
  };

  const handleRefreshItem = async (item: MarketplaceItem): Promise<MarketplaceItem | null> => {
    try {
      const resp = await fetch(`${API_BASE}/api/items/refresh`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ url: item.url, source: item.source }),
      });
      if (resp.ok) {
        const data = await resp.json();
        return {
          title: data.title || item.title,
          price_text: data.price_text || item.price_text,
          availability: data.availability || item.availability,
          url: item.url,
          source: item.source,
          image_url: data.image_url || item.image_url,
          sku: data.sku || item.sku,
        };
      }
    } catch (e) {
      console.error("Failed to refresh item:", e);
    }
    return null;
  };

  // Filter results by source if filter is active
  const filteredResults = sourceFilter
    ? results.filter(item => item.source === sourceFilter)
    : results;

  // Show login if not authenticated
  if (authLoading) {
    return <LoadingSpinner />;
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  return (
    <div>
      {loading && <LoadingSpinner />}

      <header className="app-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%", maxWidth: "1200px", margin: "0 auto" }}>
          <div className="brand" onClick={handleGoHome} style={{ cursor: "pointer" }}>
            <h1>Estima</h1>
            <span className="tagline">Best Rate, No Debate.</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
            {hasSearched && (
              <>
                <SearchHistoryMenu history={history} onSelect={handleHistorySelect} />
                <SearchForm
                  onSearch={handleSearch}
                  query={query}
                  setQuery={setQuery}
                  compact={true}
                  token={token}
                  selectedMarketplaces={selectedMarketplaces}
                  setSelectedMarketplaces={setSelectedMarketplaces}
                />
              </>
            )}
            <div className="user-menu">
              <span className="user-info">
                {user?.username}
                {isAdmin && <span className="admin-badge">Admin</span>}
              </span>
              {isAdmin && (
                <button
                  className="btn-secondary"
                  onClick={() => setShowAdminDashboard(true)}
                >
                  Users
                </button>
              )}
              <button className="btn-logout" onClick={logout}>Logout</button>
            </div>
          </div>
        </div>
      </header>

      <div className="container">

        {!hasSearched && (
          <div className="search-hero-wrapper">
            <div style={{ width: "100%", display: "flex", flexDirection: "column", alignItems: "center" }}>
              <SearchForm
                onSearch={handleSearch}
                query={query}
                setQuery={setQuery}
                token={token}
                selectedMarketplaces={selectedMarketplaces}
                setSelectedMarketplaces={setSelectedMarketplaces}
              />
              <div className="scroll-hint">
                <div className="scroll-arrow-icon" onClick={handleGoToPOSection}>▼</div>
              </div>
            </div>
          </div>
        )}

        {hasSearched && (
          <div style={{ marginTop: "2rem" }}>
            {error && <p style={{ color: "red", textAlign: "center" }}>{error}</p>}
            {isFromCache && (
              <p style={{ textAlign: "center", color: "var(--color-accent)", fontSize: "0.9rem" }}>
                ⚡ Previous search results loaded. Use Refresh (🔄️) buttons to confirm current prices & availability.
              </p>
            )}
          </div>
        )}

        {hasSearched && (
          <ResultsTable
            items={filteredResults}
            note={note}
            hasSearched={hasSearched}
            onAdd={handleAdd}
            onRemove={handleRemoveByItem}
            chosenItemIds={chosenItemIds}
            onImageClick={(src, title) => setLightbox({ src, title })}
            isFromCache={isFromCache}
            onRefreshItem={handleRefreshItem}
            sourceFilter={sourceFilter}
            onSourceFilterChange={setSourceFilter}
            allResults={results}
          />
        )}

        <div style={{ marginTop: "3rem" }}>
          <ChosenItemsTable items={chosenItems} onRemove={handleRemove} token={token || undefined} draftData={activeDraft} />
        </div>

        <POHistory token={token || undefined} isAdmin={isAdmin} onEdit={handleEditDraft} />
      </div>

      {lightbox && (
        <div
          className="lightbox-backdrop"
          onClick={() => setLightbox(null)}
          style={{
            position: "fixed", top: 0, left: 0, width: "100%", height: "100%",
            backgroundColor: "rgba(0,0,0,0.8)", display: "flex", justifyContent: "center", alignItems: "center", zIndex: 2000
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{ backgroundColor: "white", padding: "10px", borderRadius: "8px", maxWidth: "90%", maxHeight: "90%", overflow: "hidden" }}
          >
            <ImageMagnifier
              src={lightbox.src}
              alt={lightbox.title}
            />
            <div style={{ textAlign: "center", marginTop: "10px" }}>
              <button onClick={() => setLightbox(null)} className="btn-primary">Close</button>
            </div>
          </div>
        </div>
      )}

      {showAdminDashboard && (
        <AdminDashboard onClose={() => setShowAdminDashboard(false)} />
      )}
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}

export default App;
