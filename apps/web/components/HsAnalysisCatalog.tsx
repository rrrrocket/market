"use client";

import { ArrowLeft, ArrowRight, Database, Search } from "lucide-react";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { marketApi } from "@/lib/api";
import { label } from "@/lib/labels";

type Catalog = Awaited<ReturnType<typeof marketApi.hsCatalog>>;

export default function HsAnalysisCatalog() {
  const [data, setData] = useState<Catalog | null>(null);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("ALL");
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setData(await marketApi.hsCatalog({q: search, status, page, page_size: 50}));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "无法加载 HS 分析库");
    } finally {
      setLoading(false);
    }
  }, [page, search, status]);

  useEffect(() => { void load(); }, [load]);

  function submit(event: FormEvent) {
    event.preventDefault();
    setPage(1);
    setSearch(query.trim());
  }

  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return <>
    {data && <div className="catalog-stats">
      <div className="card"><small>六位 HS 总数</small><strong>{data.summary.total_hs.toLocaleString()}</strong></div>
      <div className="card"><small>已有市场分析</small><strong>{data.summary.analyzed_hs.toLocaleString()}</strong></div>
      <div className="card"><small>待生成</small><strong>{data.summary.remaining_hs.toLocaleString()}</strong></div>
      <div className="card"><small>分析覆盖率</small><strong>{data.summary.coverage_percent}%</strong></div>
    </div>}

    <section className="card catalog-table-card">
      <div className="catalog-toolbar">
        <form onSubmit={submit}><Search size={17}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索 HS、英文或中文类目"/><button className="primary">搜索</button></form>
        <select value={status} onChange={(event) => {setStatus(event.target.value); setPage(1);}}>
          <option value="ALL">全部状态</option><option value="READY">已有分析</option><option value="NOT_ANALYZED">待分析</option>
        </select>
      </div>

      {error && <div className="error">{error}</div>}
      {loading && <div className="loading">正在加载 HS 分析库…</div>}
      {!loading && data && <div className="catalog-scroll"><table className="table catalog-table">
        <thead><tr><th>HS</th><th>商品类目</th><th>状态</th><th>市场数</th><th>首选市场</th><th>分数</th><th></th></tr></thead>
        <tbody>{data.items.map((item) => <tr key={item.hs_code}>
          <td><code>{item.hs_code}</code></td>
          <td><strong>{item.name_en}</strong>{item.name_zh && <small>{item.name_zh}</small>}</td>
          <td><span className={`catalog-status status-${item.status.toLowerCase()}`}>{label(item.status)}</span></td>
          <td>{item.markets_count || "—"}</td><td>{item.top_market_name ? `${item.top_market_name} · ${item.top_market_iso3}` : "—"}</td><td>{item.top_score?.toFixed(1) ?? "—"}</td>
          <td><Link className="catalog-open" href={`/product/${item.hs_code}`}>{item.status === "READY" ? "查看" : "生成分析"}<ArrowRight size={14}/></Link></td>
        </tr>)}</tbody>
      </table></div>}

      {data && <div className="catalog-pagination"><span>第 {page} / {pages} 页 · {data.total.toLocaleString()} 项</span><div><button disabled={page <= 1} onClick={() => setPage((value) => value - 1)}><ArrowLeft size={15}/></button><button disabled={page >= pages} onClick={() => setPage((value) => value + 1)}><ArrowRight size={15}/></button></div></div>}
    </section>
    <p className="catalog-note"><Database size={15}/> 全量计算依赖 UN Comtrade 全商品数据；缺失商品不会生成推测结果。</p>
  </>;
}
