import { DataQuality, Detail, History, Opportunity, WatchlistItem } from "@/types/market";
export const API = process.env.NEXT_PUBLIC_API_BASE_URL || "";

export type CountryOpportunityItem = {
  iso3:string; name:string; name_zh:string|null; region:string|null; year:number; rank:number;
  china_import_value_usd:number|null; total_import_value_usd:number; china_share:number|null;
  yoy_growth:number|null; cagr_3y:number|null; hs_count:number; imported_hs_count:number; trend:string;
};

export type CountryOpportunityProduct = {
  hs_code:string; name_en:string; name_zh:string|null; china_import_value_usd:number|null;
  total_import_value_usd:number; unserved_value_usd:number|null; china_share:number|null;
  yoy_growth:number|null; cagr_3y:number|null; volatility:number|null; trend:string;
  history:{year:number;value_usd:number}[]; opportunity_score:number; score_coverage:number;
  opportunity_type:string; china_import_rank:number|null; opportunity_rank:number;
};

export type CountryOpportunityDetail = {
  country:{iso3:string;name:string;name_zh:string|null;region:string|null;subregion:string|null};
  origin_iso3:string; year:number;
  summary:{china_import_value_usd:number|null;total_import_value_usd:number|null;china_share:number|null;yoy_growth:number|null;cagr_3y:number|null;analyzed_hs_count:number;imported_hs_count:number};
  history:{year:number;china_import_value_usd:number|null;total_import_value_usd:number|null;china_share:number|null}[];
  products:CountryOpportunityProduct[];
  macro:Record<string,{value:number|null;value_text:string|null;unit:string|null;year:number;observed_type:string}>;
  product_pagination:{page:number;page_size:number;total:number;sort:string;q:string|null;opportunity_type:string|null};
  methodology:{score_version:string;weights:Record<string,number>};
  data_provenance:{code:"DIRECT_IMPORT"|"CHINA_MIRROR"|"BACI";label:string;priority:number;first_year:number;last_year:number}[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}/api/v1${path}`, { ...init, cache: "default", headers: {"Content-Type":"application/json", ...init?.headers} });
  if (!response.ok) throw new Error(await response.text() || `Request failed: ${response.status}`);
  if (response.status === 204) return undefined as T;
  return response.json();
}
export const marketApi = {
  search: (q:string) => request<{hs_code:string;name_en:string;name_zh:string|null;level:number}[]>(`/products/search?q=${encodeURIComponent(q)}`),
  hsCatalog: (params:{q?:string;status?:string;page?:number;page_size?:number}) => {
    const query = new URLSearchParams();
    if (params.q) query.set("q", params.q);
    if (params.status) query.set("status", params.status);
    query.set("page", String(params.page || 1));
    query.set("page_size", String(params.page_size || 50));
    return request<{summary:{total_hs:number;analyzed_hs:number;remaining_hs:number;coverage_percent:number};page:number;page_size:number;total:number;items:{hs_code:string;name_en:string;name_zh:string|null;status:string;analysis_year:number|null;markets_count:number;top_market_iso3:string|null;top_market_name:string|null;top_score:number|null;coverage:number|null;last_analyzed_at:string|null;error:string|null}[]}>(`/catalog/hs?${query}`);
  },
  comtradePipeline: () => request<{status:string;years:number[];complete_through:number;partial_years:number[];total_hs:number;batch_size:number;total_batches:number;downloaded_batches:number;imported_batches:number;download_percent:number;import_percent:number;analyzed_hs:number;analysis_percent:number;records_downloaded:number;bytes_downloaded:number;current_batch:number;current_hs:string|null;no_data_hs:number;failed_hs:number;updated_at:string|null;error:string|null}>("/admin/comtrade-pipeline"),
  countryOpportunities: () => request<{year:number;origin_iso3:string;countries:number;latest_year_counts:Record<string,number>;total_china_import_value_usd:number;items:CountryOpportunityItem[]}>("/country-opportunities"),
  countryOpportunity: (iso3:string, params:{sort?:string;q?:string;opportunity_type?:string;page?:number;page_size?:number}) => {
    const query = new URLSearchParams();
    if (params.sort) query.set("sort", params.sort);
    if (params.q) query.set("q", params.q);
    if (params.opportunity_type) query.set("opportunity_type", params.opportunity_type);
    query.set("page", String(params.page || 1));
    query.set("page_size", String(params.page_size || 50));
    return request<CountryOpportunityDetail>(`/country-opportunities/${iso3}?${query}`);
  },
  createAnalysis: (hs_code:string) => request<{id:string;status:string}>("/analyses", {method:"POST",body:JSON.stringify({hs_code,origin_iso3:"CHN"})}),
  analysis: (id:string) => request<{status:string;error_message:string|null}>(`/analyses/${id}`),
  opportunities: (hs:string) => request<Opportunity[]>(`/opportunities?hs_code=${hs}&origin_iso3=CHN&limit=250`),
  detail: (id:number) => request<Detail>(`/opportunities/${id}`),
  history: (hs:string,iso3:string) => request<History[]>(`/trade/history?hs_code=${hs}&country_iso3=${iso3}`),
  suppliers: (hs:string,iso3:string,year:number) => request<{supplier_iso3:string;supplier_name:string;trade_value_usd:number;share:number;rank:number}[]>(`/trade/suppliers?hs_code=${hs}&country_iso3=${iso3}&year=${year}`),
  syncWorldBank: (countries:string[] = []) => request<{status:string;rows_imported:number;countries_with_data:number}>("/admin/sync/world-bank", {method:"POST",body:JSON.stringify({countries})}),
  syncWits: (hs_code:string,country_iso3:string,year:number) => request<{status:string;rows_imported:number}>("/admin/sync/wits", {method:"POST",body:JSON.stringify({hs_code,origin_iso3:"CHN",countries:[country_iso3],year})}),
  syncTed: (hs_code:string,country_iso3:string,keyword:string) => request<{status:string;rows_imported:number}>("/admin/sync/explicit-demand", {method:"POST",body:JSON.stringify({hs_code,country_iso3,keyword})}),
  admin: () => request<{source_status:string;last_sync:string|null;analysis_runs:{id:string;hs_code:string;status:string;started_at:string|null;error:string|null}[];cached_products:number;trade_records:number}>("/admin/data")
  ,dataQuality: () => request<DataQuality>("/admin/data-quality")
  ,providers: () => request<{code:string;name:string;category:string;capabilities:string[];reliability:string;enabled:boolean;health:string}[]>("/integrations/providers")
  ,watchlists: () => request<WatchlistItem[]>("/watchlists")
  ,createWatchlist: (payload:{name:string;hs_code?:string;country_iso3?:string;channel?:string}) => request<WatchlistItem>("/watchlists", {method:"POST", body:JSON.stringify(payload)})
  ,deleteWatchlist: (id:number) => request<void>(`/watchlists/${id}`, {method:"DELETE"})
  ,events: () => request<{id:number;entity_type:string;entity_id:number;event_type:string;severity:string;detected_at:string}[]>("/events")
  ,importDatasetFile: (payload:{dataset_type:string;provider_code:string;format:string;content_base64:string;source_revision?:string}) => request<{job_id:string;status:string;rows_received:number;rows_imported:number;snapshot_id:number;checksum:string}>("/admin/datasets/import-file", {method:"POST", body:JSON.stringify(payload)})
};
