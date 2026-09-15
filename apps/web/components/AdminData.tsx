"use client";

import { Database, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { marketApi } from "@/lib/api";
import { label } from "@/lib/labels";

type Admin = {source_status:string;last_sync:string|null;analysis_runs:{id:string;hs_code:string;status:string;started_at:string|null;error:string|null}[];cached_products:number;trade_records:number};

export default function AdminData() {
  const [data, setData] = useState<Admin | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(() => marketApi.admin().then(setData).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "无法加载数据管理信息")), []);
  useEffect(() => { void load(); }, [load]);

  if (error) return <div className="card error">{error}</div>;
  if (!data) return <div className="card loading">正在加载数据源状态…</div>;
  return <>
    <div className="admin-stats">
      <div className="card admin-stat"><small>数据源状态</small><strong><span className="status">{label(data.source_status)}</span></strong></div>
      <div className="card admin-stat"><small>缓存商品</small><strong>{data.cached_products}</strong></div>
      <div className="card admin-stat"><small>贸易记录</small><strong>{data.trade_records.toLocaleString()}</strong></div>
    </div>
    <section className="card">
      <div className="panel-title"><h2><Database size={16} style={{display:"inline",verticalAlign:"-3px",marginRight:8}}/>分析任务</h2><button onClick={load} style={{border:0,background:"none",cursor:"pointer"}} aria-label="刷新"><RefreshCw size={16}/></button></div>
      <table className="table"><thead><tr><th>任务 ID</th><th>HS 编码</th><th>状态</th><th>开始时间</th><th>错误</th></tr></thead><tbody>{data.analysis_runs.map((run) => <tr key={run.id}><td><code>{run.id.slice(0,8)}</code></td><td>{run.hs_code}</td><td><span className="status">{label(run.status)}</span></td><td>{run.started_at ? new Date(run.started_at).toLocaleString() : "—"}</td><td>{run.error || "—"}</td></tr>)}</tbody></table>
      {!data.analysis_runs.length && <div className="empty">暂无分析任务。</div>}
    </section>
    <p style={{color:"#607087",fontSize:13,marginTop:14}}>最近同步：{data.last_sync ? new Date(data.last_sync).toLocaleString() : "尚未导入数据"}</p>
  </>;
}
