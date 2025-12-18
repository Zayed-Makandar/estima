export type MarketplaceName = "robu" | "robocraze" | "thinkrobotics" | "evelta" | "Draft";

export interface MarketplaceItem {
  title: string;
  price_text: string;
  availability: string;
  url: string;
  source: MarketplaceName;
  image_url?: string;
  sku?: string;
}

export interface SearchHistoryItem {
  id: string | number;
  query: string;
  items: MarketplaceItem[];
  items_count?: number;
  note: string | null;
  timestamp?: number;
  searched_at?: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  role: "admin" | "normal";
  is_active: boolean;
}

export interface SearchResponse {
  items: MarketplaceItem[];
  fetched_at: string;
  note: string | null;
  from_cache: boolean;
}
