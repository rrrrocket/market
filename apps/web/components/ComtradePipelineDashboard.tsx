"use client";

import { AlertTriangle, CheckCircle2, Database, Download, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { marketApi } from "@/lib/api";
import { label } from "@/lib/labels";

type Pipeline = Awaited<ReturnType<typeof marketApi.comtradePipeline>>;

function bytes(value: number) {
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`;
  return `${(value / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function Stage({label, value, detail}:{label:string;value:number;detail:string}) {
  return <div className="pipeline-stage">
    <div><strong>{label}</strong><span>{value.toFixed(1)}%</span></div>
    <div className="pipeline-track"><i style={{width:`${Math.min(100, value)}%`}}/></div>
    <small>{detail}</small>
  </div>;
}

export default function ComtradePipelineDashboard() {
  const [data, setData] = useState<Pipeline | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(() => marketApi.comtradePipeline().then(setData).catch((reason) => setError(reason instanceof Error ? reason.message : "无法加载数据处理任务")), []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(load, 5000);
    return () => window.clearInterval(timer);
  }, [load]);

  if (error) return <section className="card error">{error}</section>;
  if (!data) return <section className="card loading">正在加载本地数据处理任务…</section>;

  const active = ["DOWNLOADING", "IMPORTING", "ANALYZING"].includes(data.status);
  return <section className="card pipeline-overview">
    <div className="pipeline-heading">
      <div><div className="eyebrow">本地数据处理任务</div><h2>UN Comtrade 全量 HS 数据</h2></div>
      <span className={`pipeline-state state-${data.status.toLowerCase()}`}>{active && <RefreshCw size={13} className="spin"/>}{label(data.status)}</span>
    </div>
    <div className="pipeline-kpis">
      <div><Download size={18}/><small>本地批次</small><strong>{data.downloaded_batches} / {data.total_batches || "—"}</strong></div>
      <div><Database size={18}/><small>已下载记录</small><strong>{data.records_downloaded.toLocaleString()}</strong></div>
      <div><CheckCircle2 size={18}/><small>已分析 HS</small><strong>{data.analyzed_hs.toLocaleString()} / {data.total_hs.toLocaleString()}</strong></div>
      <div><small>本地压缩数据</small><strong>{bytes(data.bytes_downloaded)}</strong><span>{data.years[0]}–{data.years.at(-1)}</span></div>
    </div>
    <div className="pipeline-stages">
      <Stage label="01 下载并校验" value={data.download_percent} detail={`当前批次 ${data.current_batch || 0}；每批 ${data.batch_size} 个 HS`}/>
      <Stage label="02 导入本地数据库" value={data.import_percent} detail={`${data.imported_batches} 个压缩文件已导入`}/>
      <Stage
        label="03 生成市场分析"
        value={data.analysis_percent}
        detail={active && data.current_hs
          ? `正在处理 HS ${data.current_hs}`
          : `${data.analyzed_hs} 个已分析；${data.no_data_hs} 个暂无数据；${data.failed_hs} 个失败`}
      />
    </div>
    {data.partial_years.length > 0 && <div className="pipeline-notice"><AlertTriangle size={16}/>{data.partial_years.join("、")} 为未完整年度；市场排名使用 {data.complete_through} 年。</div>}
    {data.error && <div className="pipeline-error">{data.error}</div>}
  </section>;
}
