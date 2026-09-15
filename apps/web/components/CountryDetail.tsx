"use client";

import { Database, Info, RefreshCw, ShieldAlert, Store, Truck } from "lucide-react";
import { useEffect, useState } from "react";

import { marketApi } from "@/lib/api";
import { Detail, Opportunity } from "@/types/market";
import TrendChart from "./TrendChart";

const pct = (value: number | null) => value === null ? "—" : `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;
const score = (value: number | null) => value === null ? "No data" : value.toFixed(0);
const money = (value:number|null,currency="USD") => {
  if (value === null) return "—";
  try { return new Intl.NumberFormat("en", {style:"currency",currency,notation:"compact",maximumFractionDigits:1}).format(value); }
  catch { return `${new Intl.NumberFormat("en", {notation:"compact",maximumFractionDigits:1}).format(value)} ${currency}`; }
};

function ScoreCard({label, value, state}:{label:string;value:number|null;state?:string}) {
  return <div className={`score-card ${value === null ? "score-card-empty" : ""}`}>
    <span>{label}</span><strong>{score(value)}</strong><small>{value === null ? state || "Not connected" : "0–100"}</small>
  </div>;
}

export default function CountryDetail({hs, iso3}:{hs:string;iso3:string}) {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [suppliers, setSuppliers] = useState<{supplier_iso3:string;supplier_name:string;trade_value_usd:number;share:number;rank:number}[]>([]);
  const [productName, setProductName] = useState(`HS ${hs}`);
  const [error, setError] = useState("");
  const [enrichment, setEnrichment] = useState("");

  useEffect(() => {
    (async () => {
      try {
        marketApi.search(hs).then((products) => {
          const exact = products.find((product) => product.hs_code === hs);
          if (exact) setProductName(exact.name_en);
        }).catch(() => undefined);
        let rows = await marketApi.opportunities(hs);
        if (!rows.length) {
          const run = await marketApi.createAnalysis(hs);
          for (let index = 0; index < 20; index += 1) {
            await new Promise((resolve) => setTimeout(resolve, 500));
            const status = await marketApi.analysis(run.id);
            if (status.status === "COMPLETED") break;
          }
          rows = await marketApi.opportunities(hs);
        }
        const item = rows.find((row: Opportunity) => row.destination_iso3 === iso3);
        if (!item) throw new Error("Country is not available in this analysis");
        const full = await marketApi.detail(item.id);
        setDetail(full);
        setSuppliers(await marketApi.suppliers(hs, iso3, full.period_year));
      } catch (reason: unknown) {
        setError(reason instanceof Error ? reason.message : "Unable to load opportunity");
      }
    })();
  }, [hs, iso3]);

  if (error) return <div className="card error">{error}</div>;
  if (!detail) return <div className="card loading">Loading opportunity evidence…</div>;
  const currentDetail = detail;

  async function enrich() {
    setEnrichment("Syncing World Bank, WITS and TED…");
    const results = await Promise.allSettled([
      marketApi.syncWorldBank([iso3]),
      marketApi.syncWits(hs, iso3, currentDetail.period_year),
      marketApi.syncTed(hs, iso3, productName),
    ]);
    const completed = results.filter((item) => item.status === "fulfilled").length;
    setEnrichment(`${completed}/3 sources synced; refreshing…`);
    window.setTimeout(() => window.location.reload(), 700);
  }

  return <>
    <div className="opportunity-heading">
      <div><div className="eyebrow">{productName} · {iso3}</div><h1 className="page-title">{detail.country_name}</h1><p className="subtitle">HS {hs} · All channels · {detail.period_year}</p></div>
      <div className="opportunity-actions"><button className="secondary-action" onClick={enrich} disabled={Boolean(enrichment)}><RefreshCw size={14} className={enrichment ? "spin" : ""}/>{enrichment || "同步外部数据"}</button><div className="confidence-badge"><span>Confidence</span><strong>{detail.scores.confidence?.toFixed(0) ?? "—"}</strong><small>{detail.confidence_label}</small></div></div>
    </div>

    <section className="score-surface card">
      <div className="score-primary"><span>{detail.scores.distribution_opportunity === null ? "Market Attractiveness" : "Distribution Opportunity"}</span><strong>{score(detail.scores.distribution_opportunity ?? detail.scores.market_attractiveness)}</strong><small>{detail.scores.distribution_opportunity === null ? "Full opportunity score unavailable until supply and economics are connected." : "Decision score"}</small></div>
      <div className="score-grid">
        <ScoreCard label="Structural demand" value={detail.scores.structural_demand}/>
        <ScoreCard label="Digital demand" value={detail.scores.digital_demand}/>
        <ScoreCard label="Marketplace" value={detail.scores.marketplace_demand}/>
        <ScoreCard label="Explicit demand" value={detail.scores.explicit_demand}/>
        <ScoreCard label="Supply fit" value={detail.scores.supply_fit}/>
        <ScoreCard label="Economics" value={detail.scores.economics} state="Not enough data"/>
        <ScoreCard label="Market access" value={detail.scores.market_access}/>
        <ScoreCard label="Risk" value={detail.scores.risk} state="Unknown"/>
      </div>
    </section>

    <div className="detail-grid">
      <section className="card insight"><div className="section-label">Why this market?</div><ul className="reasons">{detail.reasons.map((reason, index) => <li key={index}><b className={reason.sentiment === "negative" ? "negative" : ""}>{reason.sentiment === "negative" ? "−" : "+"}</b>{reason.text}</li>)}</ul><p className="provenance-note">Generated only from linked evidence; no sales forecast.</p></section>
      <section className="card"><div className="panel-title"><h2>Demand layers</h2><span>connection status</span></div><div className="layer-list">{["STRUCTURAL", "DIGITAL", "MARKETPLACE", "EXPLICIT"].map((layer) => <div key={layer}><span>{layer.toLowerCase().replace("marketplace", "Marketplace")}</span><strong>{detail.signals[layer]?.length ? `${detail.signals[layer].length} signals` : "No data connected"}</strong></div>)}</div></section>
    </div>

    <div className="section-grid detail-sections">
      <section className="card chart-card"><div className="chart-title"><div><h2>Structural trade demand</h2><p>Importer-reported imports; five complete years</p></div></div><TrendChart history={detail.history}/></section>
      <section className="card"><div className="panel-title"><h2>Supplier countries</h2><span>share of destination imports</span></div><table className="table"><tbody>{suppliers.slice(0, 6).map((supplier) => <tr key={supplier.supplier_iso3}><td>#{supplier.rank}</td><td><strong>{supplier.supplier_name}</strong><small>{supplier.supplier_iso3}</small></td><td><div className="bar"><i style={{width:`${Math.min(100, supplier.share * 100)}%`}}/></div></td><td>{(supplier.share * 100).toFixed(1)}%</td></tr>)}</tbody></table></section>
      <section className="card intelligence-block"><div className="block-icon"><Store size={19}/></div><div><h2>China supply</h2><strong>{detail.supply.status === "CONNECTED" ? "Connected" : "Not connected"}</strong><p>Supplier count, offers, cost, MOQ, stock, lead time, and capabilities will appear only from the Supplier Network API.</p></div></section>
      <section className="card intelligence-block"><div className="block-icon"><Truck size={19}/></div><div><h2>Economics</h2><strong>{detail.economics.status === "AVAILABLE" ? "Available" : "Not enough data"}</strong><p>Landed cost, channel fees, contribution margin, and break-even price remain empty until verified inputs exist.</p></div></section>
      <section className="card intelligence-block"><div className="block-icon"><ShieldAlert size={19}/></div><div><h2>Market access & tariff</h2><strong>{detail.market_access ? `${detail.market_access.china_applicable_tariff?.toFixed(2) ?? "—"}% China applicable tariff` : "Not synced"}</strong><p>{detail.market_access ? `MFN ${detail.market_access.mfn_tariff?.toFixed(2) ?? "—"}% · ${detail.market_access.period_year} · ${detail.market_access.observed_type}` : "Use Sync external data to retrieve the reported WITS / UNCTAD TRAINS rate for this HS and destination."}</p></div></section>
      <section className="card intelligence-block"><div className="block-icon"><Info size={19}/></div><div><h2>China position</h2><strong>{pct(detail.china_share)}</strong><p>Share of destination imports reported as originating in China. It is not a supply-fit score.</p></div></section>
      <section className="card intelligence-block"><div className="block-icon"><Database size={19}/></div><div><h2>Country capacity</h2><strong>{detail.macro.gdp_usd ? money(detail.macro.gdp_usd.value) : "Not synced"}</strong><p>{detail.macro.gdp_per_capita ? `GDP per capita ${money(detail.macro.gdp_per_capita.value)} · ${detail.macro.gdp_per_capita.year}` : "World Bank GDP, consumption, population and digital-access indicators appear after synchronization."}</p></div></section>
    </div>

    <section className="card evidence-section"><div className="panel-title"><h2>Observed public tenders</h2><span>TED EU · {detail.explicit_demands.length} matched</span></div>{detail.explicit_demands.length ? <div className="table-wrap"><table className="table"><thead><tr><th>Published</th><th>Buyer</th><th>Tender</th><th>Budget</th><th>Status</th></tr></thead><tbody>{detail.explicit_demands.map((tender) => <tr key={tender.id}><td>{new Date(tender.published_at).toLocaleDateString()}</td><td>{tender.buyer_name || "—"}</td><td>{tender.source_url ? <a className="catalog-open" href={tender.source_url} target="_blank" rel="noreferrer">{tender.title}</a> : tender.title}</td><td>{money(tender.budget_max,tender.currency || "EUR")}</td><td>{tender.status}</td></tr>)}</tbody></table></div> : <div className="empty-state"><strong>No matched tender observations</strong><span>Synchronize this market to search active TED notices using the registered HS product description.</span></div>}</section>

    <section className="card evidence-section"><div className="panel-title"><h2><Database size={17}/> Evidence registry</h2><span>{detail.evidence.length} linked facts</span></div><div className="table-wrap"><table className="table"><thead><tr><th>Metric</th><th>Value</th><th>Source</th><th>Type</th><th>Reliability</th><th>Period</th><th>Retrieved</th></tr></thead><tbody>{detail.evidence.map((evidence) => <tr key={`${evidence.id}-${evidence.metric_key}`}><td>{evidence.metric_key}</td><td><strong>{evidence.display_value}</strong></td><td>{evidence.source_identifier}{evidence.notes && <small>{evidence.notes}</small>}</td><td><span className="data-badge">{evidence.observed_type || "REPORTED"}</span></td><td>{evidence.source_reliability || "A"}</td><td>{evidence.period}</td><td>{new Date(evidence.retrieved_at).toLocaleDateString()}</td></tr>)}</tbody></table></div></section>
  </>;
}
