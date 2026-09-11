"use client";

import { Activity, AlertTriangle, CheckCircle2, Database, Link2Off, ShieldCheck } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { marketApi } from "@/lib/api";
import { DataQuality } from "@/types/market";

function statusClass(status: string) {
  if (["READY", "AVAILABLE", "TEST_DATA"].includes(status)) return "quality-good";
  if (["DISABLED", "NOT_CONNECTED", "AUTH_REQUIRED"].includes(status)) return "quality-neutral";
  return "quality-warn";
}

export default function DataQualityDashboard() {
  const [quality, setQuality] = useState<DataQuality | null>(null);
  const [error, setError] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [datasetType, setDatasetType] = useState("MACRO");
  const [providerCode, setProviderCode] = useState("WORLD_BANK");
  const [importStatus, setImportStatus] = useState("");

  useEffect(() => {
    marketApi.dataQuality().then(setQuality).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : "Unable to load data quality");
    });
  }, []);

  if (error) return <div className="card error">{error}</div>;
  if (!quality) return <div className="card loading">Loading data quality…</div>;

  const coverage = [
    ["Trade observations", quality.coverage.trade_observations ?? 0],
    ["Demand signals", quality.coverage.demand_signals ?? 0],
    ["Tariff records", quality.coverage.tariff_records ?? 0],
    ["Macro records", quality.coverage.macro_records ?? 0],
    ["Opportunities", quality.coverage.opportunities ?? 0],
  ];

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setImportStatus("Importing…");
    try {
      const contentBase64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(file);
      });
      const format = file.name.toLowerCase().endsWith(".parquet") ? "PARQUET" : file.name.toLowerCase().endsWith(".csv") ? "CSV" : "JSON";
      const result = await marketApi.importDatasetFile({dataset_type:datasetType, provider_code:providerCode, format, content_base64:contentBase64});
      setImportStatus(`${result.rows_imported} of ${result.rows_received} rows imported · ${result.status}`);
    } catch (reason: unknown) {
      setImportStatus(reason instanceof Error ? reason.message : "Import failed");
    }
  }

  return <>
    <div className="quality-summary">
      <div className="card quality-stat"><Database size={18}/><span>Canonical records</span><strong>{coverage.reduce((sum, row) => sum + Number(row[1]), 0).toLocaleString()}</strong></div>
      <div className="card quality-stat"><AlertTriangle size={18}/><span>Failed syncs</span><strong>{quality.failed_syncs}</strong></div>
      <div className="card quality-stat"><Link2Off size={18}/><span>Missing HS mappings</span><strong>{quality.missing_hs_mappings}</strong></div>
      <div className="card quality-stat"><ShieldCheck size={18}/><span>Low confidence</span><strong>{quality.low_confidence_opportunities}</strong></div>
    </div>

    <div className="quality-grid">
      <section className="card">
        <div className="panel-title"><h2><Activity size={17}/> Provider health</h2><span>{quality.provider_health.length} registered</span></div>
        <div className="provider-list">
          {quality.provider_health.map((provider) => <div className="provider-row" key={provider.code}>
            <div><strong>{provider.name}</strong><small>{provider.category} · Reliability {provider.reliability}</small></div>
            <span className={`quality-pill ${statusClass(provider.status)}`}>{provider.status.replaceAll("_", " ")}</span>
          </div>)}
        </div>
      </section>
      <section className="card">
        <div className="panel-title"><h2><CheckCircle2 size={17}/> Data coverage</h2><span>stored rows</span></div>
        <div className="coverage-list">
          {coverage.map(([label, value]) => <div key={label}><span>{label}</span><strong>{Number(value).toLocaleString()}</strong></div>)}
        </div>
        <div className="quality-note"><strong>Recent revisions</strong><span>{quality.recent_revisions}</span></div>
        <div className="quality-note"><strong>Stale sources</strong><span>{quality.stale_sources.length ? quality.stale_sources.join(", ") : "None"}</span></div>
      </section>
    </div>
    <section className="card dataset-import">
      <div><h2>Manual dataset ingestion</h2><p>CSV, JSON, or Parquet is snapshotted before registered trade, tariff, or macro normalization.</p></div>
      <form onSubmit={upload}>
        <select value={datasetType} onChange={(event) => { setDatasetType(event.target.value); setProviderCode(event.target.value === "MACRO" ? "WORLD_BANK" : event.target.value === "TARIFF" ? "WITS_TRAINS" : "UN_COMTRADE"); }} aria-label="Dataset type"><option value="TRADE">Trade</option><option value="TARIFF">Tariff</option><option value="MACRO">Macro</option></select>
        <input type="file" accept=".csv,.json,.parquet" onChange={(event) => setFile(event.target.files?.[0] || null)} required />
        <button className="primary">Import dataset</button>
      </form>
      {importStatus && <span className="import-result">{importStatus}</span>}
    </section>
  </>;
}
