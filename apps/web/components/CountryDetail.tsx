"use client";

import { Database, Info, ShieldAlert, Store, Truck } from "lucide-react";
import { useEffect, useState } from "react";

import { marketApi } from "@/lib/api";
import { Detail, Opportunity } from "@/types/market";
import TrendChart from "./TrendChart";

const pct = (value: number | null) => value === null ? "—" : `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;
const score = (value: number | null) => value === null ? "No data" : value.toFixed(0);

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

  return <>
    <div className="opportunity-heading">
      <div><div className="eyebrow">{productName} · {iso3}</div><h1 className="page-title">{detail.country_name}</h1><p className="subtitle">HS {hs} · All channels · {detail.period_year}</p></div>
      <div className="confidence-badge"><span>Confidence</span><strong>{detail.scores.confidence?.toFixed(0) ?? "—"}</strong><small>{detail.confidence_label}</small></div>
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
      <section className="card intelligence-block"><div className="block-icon"><ShieldAlert size={19}/></div><div><h2>Market access & risk</h2><strong>{detail.risk.length ? `${detail.risk.length} assessed risks` : "Unknown"}</strong><p>Tariff, regulatory, logistics, payment, currency, and policy risk are never assumed to be low when evidence is absent.</p></div></section>
      <section className="card intelligence-block"><div className="block-icon"><Info size={19}/></div><div><h2>China position</h2><strong>{pct(detail.china_share)}</strong><p>Share of destination imports reported as originating in China. It is not a supply-fit score.</p></div></section>
    </div>

    <section className="card evidence-section"><div className="panel-title"><h2><Database size={17}/> Evidence registry</h2><span>{detail.evidence.length} linked facts</span></div><div className="table-wrap"><table className="table"><thead><tr><th>Metric</th><th>Value</th><th>Source</th><th>Type</th><th>Reliability</th><th>Period</th><th>Retrieved</th></tr></thead><tbody>{detail.evidence.map((evidence) => <tr key={`${evidence.id}-${evidence.metric_key}`}><td>{evidence.metric_key}</td><td><strong>{evidence.display_value}</strong></td><td>{evidence.source_identifier}{evidence.notes && <small>{evidence.notes}</small>}</td><td><span className="data-badge">{evidence.observed_type || "REPORTED"}</span></td><td>{evidence.source_reliability || "A"}</td><td>{evidence.period}</td><td>{new Date(evidence.retrieved_at).toLocaleDateString()}</td></tr>)}</tbody></table></div></section>
  </>;
}
