import { DataQuality, Detail, History, Opportunity, WatchlistItem } from "@/types/market";
export const API = process.env.NEXT_PUBLIC_API_BASE_URL || "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}/api/v1${path}`, { ...init, cache: "no-store", headers: {"Content-Type":"application/json", ...init?.headers} });
  if (!response.ok) throw new Error(await response.text() || `Request failed: ${response.status}`);
  if (response.status === 204) return undefined as T;
  return response.json();
}
export const marketApi = {
  search: (q:string) => request<{hs_code:string;name_en:string;name_zh:string|null;level:number}[]>(`/products/search?q=${encodeURIComponent(q)}`),
  createAnalysis: (hs_code:string) => request<{id:string;status:string}>("/analyses", {method:"POST",body:JSON.stringify({hs_code,origin_iso3:"CHN"})}),
  analysis: (id:string) => request<{status:string;error_message:string|null}>(`/analyses/${id}`),
  opportunities: (hs:string) => request<Opportunity[]>(`/opportunities?hs_code=${hs}&origin_iso3=CHN`),
  detail: (id:number) => request<Detail>(`/opportunities/${id}`),
  history: (hs:string,iso3:string) => request<History[]>(`/trade/history?hs_code=${hs}&country_iso3=${iso3}`),
  suppliers: (hs:string,iso3:string,year:number) => request<{supplier_iso3:string;supplier_name:string;trade_value_usd:number;share:number;rank:number}[]>(`/trade/suppliers?hs_code=${hs}&country_iso3=${iso3}&year=${year}`),
  admin: () => request<{source_status:string;last_sync:string|null;analysis_runs:{id:string;hs_code:string;status:string;started_at:string|null;error:string|null}[];cached_products:number;trade_records:number}>("/admin/data")
  ,dataQuality: () => request<DataQuality>("/admin/data-quality")
  ,providers: () => request<{code:string;name:string;category:string;capabilities:string[];reliability:string;enabled:boolean;health:string}[]>("/integrations/providers")
  ,watchlists: () => request<WatchlistItem[]>("/watchlists")
  ,createWatchlist: (payload:{name:string;hs_code?:string;country_iso3?:string;channel?:string}) => request<WatchlistItem>("/watchlists", {method:"POST", body:JSON.stringify(payload)})
  ,deleteWatchlist: (id:number) => request<void>(`/watchlists/${id}`, {method:"DELETE"})
  ,events: () => request<{id:number;entity_type:string;entity_id:number;event_type:string;severity:string;detected_at:string}[]>("/events")
  ,importDatasetFile: (payload:{dataset_type:string;provider_code:string;format:string;content_base64:string;source_revision?:string}) => request<{job_id:string;status:string;rows_received:number;rows_imported:number;snapshot_id:number;checksum:string}>("/admin/datasets/import-file", {method:"POST", body:JSON.stringify(payload)})
};
