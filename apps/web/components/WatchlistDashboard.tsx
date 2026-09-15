"use client";

import { Bell, Plus, Trash2 } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { marketApi } from "@/lib/api";
import { WatchlistItem } from "@/types/market";

export default function WatchlistDashboard() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [hsCode, setHsCode] = useState("902620");
  const [country, setCountry] = useState("TUR");
  const [error, setError] = useState("");
  const load = useCallback(() => marketApi.watchlists().then(setItems).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "无法加载观察清单")), []);

  useEffect(() => { void load(); }, [load]);

  async function add(event: FormEvent) {
    event.preventDefault();
    setError("");
    await marketApi.createWatchlist({name: `HS ${hsCode} · ${country}`, hs_code: hsCode, country_iso3: country});
    await load();
  }

  async function remove(id: number) {
    await marketApi.deleteWatchlist(id);
    await load();
  }

  return <div className="watchlist-layout">
    <form className="card watchlist-form" onSubmit={add}>
      <h2><Plus size={18}/> 添加观察目标</h2>
      <label>HS 编码<input value={hsCode} onChange={(event) => setHsCode(event.target.value)} pattern="\d{2,10}" required /></label>
      <label>国家 ISO3<input value={country} onChange={(event) => setCountry(event.target.value.toUpperCase())} minLength={3} maxLength={3} required /></label>
      <button className="primary">加入观察清单</button>
      {error && <p className="error-inline">{error}</p>}
    </form>
    <section className="card">
      <div className="panel-title"><h2><Bell size={17}/> 观察清单</h2><span>{items.length} 个目标</span></div>
      {items.length === 0 ? <div className="empty-state"><Bell size={22}/><strong>尚未添加观察目标</strong><span>添加 HS 与国家组合，以便持续监测后续信号。</span></div> : items.map((item) => <div className="watch-row" key={item.id}>
        <div><strong>{item.name}</strong><small>{item.hs_code ? `HS ${item.hs_code}` : "全部商品"} · {item.country_iso3 || "全球"} · {item.channel || "全部渠道"}</small></div>
        <button type="button" onClick={() => remove(item.id)} aria-label={`删除 ${item.name}`}><Trash2 size={16}/></button>
      </div>)}
    </section>
  </div>;
}
