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
  const load = useCallback(() => marketApi.watchlists().then(setItems).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load watchlist")), []);

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
      <h2><Plus size={18}/> Add watch target</h2>
      <label>HS code<input value={hsCode} onChange={(event) => setHsCode(event.target.value)} pattern="\d{2,10}" required /></label>
      <label>Country ISO3<input value={country} onChange={(event) => setCountry(event.target.value.toUpperCase())} minLength={3} maxLength={3} required /></label>
      <button className="primary">Add to watchlist</button>
      {error && <p className="error-inline">{error}</p>}
    </form>
    <section className="card">
      <div className="panel-title"><h2><Bell size={17}/> Watchlist</h2><span>{items.length} targets</span></div>
      {items.length === 0 ? <div className="empty-state"><Bell size={22}/><strong>No watch targets yet</strong><span>Add an HS and country pair to monitor future signals.</span></div> : items.map((item) => <div className="watch-row" key={item.id}>
        <div><strong>{item.name}</strong><small>{item.hs_code ? `HS ${item.hs_code}` : "Any product"} · {item.country_iso3 || "Global"} · {item.channel || "All channels"}</small></div>
        <button type="button" onClick={() => remove(item.id)} aria-label={`Remove ${item.name}`}><Trash2 size={16}/></button>
      </div>)}
    </section>
  </div>;
}
