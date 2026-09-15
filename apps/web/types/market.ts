export type Opportunity = {
  id: number; rank: number; hs_code: string; destination_iso3: string; country_name: string;
  region: string; period_year: number; score: number; coverage: number; import_value_usd: number;
  cagr_3y: number | null; yoy_growth: number | null; china_share: number | null;
  size_score: number | null; growth_score: number | null; momentum_score: number | null; stability_score: number | null;
};
export type History = { year: number; import_value_usd: number; china_value_usd: number | null; china_share: number | null };
export type ScoreSet = {
  market_attractiveness: number | null;
  structural_demand: number | null;
  digital_demand: number | null;
  marketplace_demand: number | null;
  explicit_demand: number | null;
  market_access: number | null;
  country_capacity: number | null;
  supply_fit: number | null;
  economics: number | null;
  risk: number | null;
  distribution_opportunity: number | null;
  confidence: number | null;
};
export type Signal = {metric_key:string;value_numeric:number|null;value_text:string|null;normalized_value:number|null;observed_type:string;reliability:string;freshness:string;confidence:number|null};
export type Detail = Opportunity & {
  history: History[];
  evidence: Evidence[];
  reasons: {sentiment:string;text:string}[];
  score_version: string;
  scores: ScoreSet;
  confidence_label: string;
  signals: Record<string, Signal[]>;
  macro: Record<string,{value:number|null;value_text:string|null;unit:string|null;year:number;observed_type:string}>;
  market_access: {hs_code:string;country_iso3:string;origin_iso3:string;period_year:number;mfn_tariff:number|null;preferential_tariff:number|null;china_applicable_tariff:number|null;duty_free_flag:boolean|null;market_access_score:number|null;observed_type:string;retrieved_at:string}|null;
  explicit_demands: {id:number;buyer_name:string|null;title:string;budget_max:number|null;currency:string|null;deadline:string|null;published_at:string;source_url:string|null;status:string;observed_type:string}[];
  supply: Record<string, unknown> & {status:string};
  economics: Record<string, unknown> & {status:string};
  risk: {risk_type:string;score:number|null;reason:string|null;status:string;evidence_ids:number[]}[];
  recommendations: {recommendation:string;reason:string;confidence:number|null}[];
};
export type Evidence = {id?:number;metric_key:string;source_type:string;source_identifier:string;source_url?:string|null;source_reliability?:string;observed_type?:string;freshness?:string;period:string;display_value:string;retrieved_at:string;confidence?:number|null;notes:string|null};

export type ProviderHealth = {code:string;name:string;category:string;enabled:boolean;status:string;connector_status:string;record_count:number;reliability:string;last_success_at:string|null;last_failure_at:string|null;freshness_ttl_hours:number|null};
export type DataQuality = {generated_at:string;provider_health:ProviderHealth[];coverage:Record<string,number>;stale_sources:string[];failed_syncs:number;missing_hs_mappings:number;low_confidence_opportunities:number;source_reliability:Record<string,number>;recent_revisions:number};
export type WatchlistItem = {id:number;name:string;product_id:number|null;hs_code:string|null;country_iso3:string|null;channel:string|null;enabled:boolean;created_at:string};
