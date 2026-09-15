"use client";

import { Activity, AlertTriangle, CheckCircle2, Database, Link2Off, ShieldCheck } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { marketApi } from "@/lib/api";
import { label } from "@/lib/labels";
import { DataQuality } from "@/types/market";

function statusClass(status: string) {
  if (["READY", "DATA_READY", "TEST_DATA"].includes(status)) return "quality-good";
  if (["DISABLED", "NOT_CONNECTED", "AUTH_REQUIRED", "CONNECTOR_AVAILABLE"].includes(status)) return "quality-neutral";
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
      setError(reason instanceof Error ? reason.message : "无法加载数据质量信息");
    });
  }, []);

  if (error) return <div className="card error">{error}</div>;
  if (!quality) return <div className="card loading">正在加载数据质量信息…</div>;

  const coverage = [
    ["贸易观测记录", quality.coverage.trade_observations ?? 0],
    ["需求信号", quality.coverage.demand_signals ?? 0],
    ["关税记录", quality.coverage.tariff_records ?? 0],
    ["宏观指标", quality.coverage.macro_records ?? 0],
    ["招标记录", quality.coverage.tender_records ?? 0],
    ["市场机会", quality.coverage.opportunities ?? 0],
  ];

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setImportStatus("正在导入…");
    try {
      const contentBase64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(file);
      });
      const format = file.name.toLowerCase().endsWith(".parquet") ? "PARQUET" : file.name.toLowerCase().endsWith(".csv") ? "CSV" : "JSON";
      const result = await marketApi.importDatasetFile({dataset_type:datasetType, provider_code:providerCode, format, content_base64:contentBase64});
      setImportStatus(`已导入 ${result.rows_imported} / ${result.rows_received} 行 · ${label(result.status)}`);
    } catch (reason: unknown) {
      setImportStatus(reason instanceof Error ? reason.message : "导入失败");
    }
  }

  return <>
    <div className="quality-summary">
      <div className="card quality-stat"><Database size={18}/><span>标准化记录</span><strong>{coverage.reduce((sum, row) => sum + Number(row[1]), 0).toLocaleString()}</strong></div>
      <div className="card quality-stat"><AlertTriangle size={18}/><span>同步失败</span><strong>{quality.failed_syncs}</strong></div>
      <div className="card quality-stat"><Link2Off size={18}/><span>缺失 HS 映射</span><strong>{quality.missing_hs_mappings}</strong></div>
      <div className="card quality-stat"><ShieldCheck size={18}/><span>低置信度机会</span><strong>{quality.low_confidence_opportunities}</strong></div>
    </div>

    <div className="quality-grid">
      <section className="card">
        <div className="panel-title"><h2><Activity size={17}/> 数据源状态</h2><span>{quality.provider_health.length} 个已注册</span></div>
        <div className="provider-list">
          {quality.provider_health.map((provider) => <div className="provider-row" key={provider.code}>
            <div><strong>{provider.name}</strong><small>{label(provider.category)} · 可靠性 {provider.reliability} · {provider.record_count.toLocaleString()} 条{provider.last_success_at ? ` · 同步于 ${new Date(provider.last_success_at).toLocaleDateString()}` : ""}</small></div>
            <span className={`quality-pill ${statusClass(provider.status)}`}>{label(provider.status)}</span>
          </div>)}
        </div>
      </section>
      <section className="card">
        <div className="panel-title"><h2><CheckCircle2 size={17}/> 数据覆盖</h2><span>已存储记录</span></div>
        <div className="coverage-list">
          {coverage.map(([label, value]) => <div key={label}><span>{label}</span><strong>{Number(value).toLocaleString()}</strong></div>)}
        </div>
        <div className="quality-note"><strong>近期修订</strong><span>{quality.recent_revisions}</span></div>
        <div className="quality-note"><strong>过期数据源</strong><span>{quality.stale_sources.length ? quality.stale_sources.join(", ") : "无"}</span></div>
      </section>
    </div>
    <section className="card dataset-import">
      <div><h2>手动导入数据集</h2><p>CSV、JSON 或 Parquet 文件会先保存原始快照，再进行贸易、关税或宏观数据标准化。</p></div>
      <form onSubmit={upload}>
        <select value={datasetType} onChange={(event) => { setDatasetType(event.target.value); setProviderCode(event.target.value === "MACRO" ? "WORLD_BANK" : event.target.value === "TARIFF" ? "WITS_TRAINS" : "UN_COMTRADE"); }} aria-label="数据集类型"><option value="TRADE">贸易</option><option value="TARIFF">关税</option><option value="MACRO">宏观</option></select>
        <input type="file" accept=".csv,.json,.parquet" onChange={(event) => setFile(event.target.files?.[0] || null)} required />
        <button className="primary">导入数据集</button>
      </form>
      {importStatus && <span className="import-result">{importStatus}</span>}
    </section>
  </>;
}
