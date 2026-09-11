"use client";

import { ArrowRight, Database, Globe2, Radar, Search, ShieldCheck, Warehouse } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { marketApi } from "@/lib/api";

type Product = { hs_code: string; name_en: string; name_zh: string | null; level: number };
type Provider = {code:string;name:string;category:string;capabilities:string[];reliability:string;enabled:boolean;health:string};
type Event = {id:number;entity_type:string;entity_id:number;event_type:string;severity:string;detected_at:string};

export default function Home() {
  const [query, setQuery] = useState("902620");
  const [results, setResults] = useState<Product[]>([]);
  const [selected, setSelected] = useState<Product | null>(null);
  const [open, setOpen] = useState(false);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const router = useRouter();

  useEffect(() => {
    Promise.all([marketApi.providers(), marketApi.events()]).then(([providerRows, eventRows]) => {
      setProviders(providerRows);
      setEvents(eventRows);
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    const value = query.trim();
    if (value.length < 2) { setResults([]); return; }
    const timer = window.setTimeout(() => {
      marketApi.search(value).then((products) => {
        setResults(products.slice(0, 8));
        if (/^\d+$/.test(value)) setSelected(products.find((product) => product.hs_code === value) || null);
      }).catch(() => setResults([]));
    }, 180);
    return () => window.clearTimeout(timer);
  }, [query]);

  function choose(product: Product) {
    setSelected(product);
    setQuery(product.hs_code);
    setOpen(false);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    let product = selected;
    if (!product || query !== product.hs_code) product = (await marketApi.search(query.trim()))[0] || null;
    if (product) router.push(`/product/${product.hs_code}`);
  }

  const connected = providers.filter((provider) => provider.enabled && ["AVAILABLE", "TEST_DATA"].includes(provider.health));
  const liveConnected = connected.filter((provider) => provider.health !== "TEST_DATA");

  return <main className="shell overview-page">
    <section className="overview-head">
      <div><div className="eyebrow">Global Distribution Intelligence</div><h1>从全球需求证据，走到可执行的市场机会</h1><p>先验证需求，再连接中国供给、成本和风险。缺失的数据保持为空，不用推测填补。</p></div>
      <div className="system-readiness"><span>Live data readiness</span><strong>{liveConnected.length}<small> / {providers.length || "—"}</small></strong><p>{providers.length ? "official providers available" : "checking providers"}</p></div>
    </section>

    <form className="searchbox product-search overview-search" onSubmit={submit}>
      <Search size={20} className="search-icon" />
      <div className="search-field">
        <input aria-label="HS Code or product keyword" value={query} autoComplete="off" onChange={(event) => { setQuery(event.target.value); setOpen(true); }} onFocus={() => setOpen(true)} placeholder="输入 HS Code、商品或供应商商品" />
        {selected && query === selected.hs_code && <span className="selected-category">{selected.name_en}</span>}
        {open && results.length > 0 && <div className="product-results">{results.map((product) => <button type="button" key={product.hs_code} onClick={() => choose(product)}><strong>HS {product.hs_code}</strong><span>{product.name_en}</span><small>{product.level}-digit HS 2022</small></button>)}</div>}
      </div>
      <button className="primary">分析全球市场 <ArrowRight size={16}/></button>
    </form>

    <div className="intelligence-path">
      <div className="path-card path-active"><Globe2 size={20}/><span>Structural demand</span><strong>Connected</strong><small>Importer-reported trade</small></div>
      <div className="path-arrow">→</div>
      <div className="path-card"><ShieldCheck size={20}/><span>Market access</span><strong>{providers.some((provider) => provider.category === "TARIFF" && provider.enabled) ? "Connected" : "Not connected"}</strong><small>Tariff and restrictions</small></div>
      <div className="path-arrow">→</div>
      <div className="path-card"><Warehouse size={20}/><span>China supply</span><strong>{providers.some((provider) => provider.category === "SUPPLY" && provider.enabled) ? "Connected" : "Not connected"}</strong><small>Offers, MOQ, stock</small></div>
      <div className="path-arrow">→</div>
      <div className="path-card"><Radar size={20}/><span>Opportunity</span><strong>Evidence gated</strong><small>No synthetic score</small></div>
    </div>

    <div className="overview-grid">
      <section className="card opportunity-feed">
        <div className="panel-title"><h2><Radar size={17}/> Opportunity feed</h2><span>evidence-backed events</span></div>
        {events.length ? events.slice(0, 8).map((item) => <div className="feed-row" key={item.id}><span className={`severity severity-${item.severity.toLowerCase()}`}>{item.severity}</span><div><strong>{item.event_type.replaceAll("_", " ")}</strong><small>{item.entity_type} #{item.entity_id} · {new Date(item.detected_at).toLocaleDateString()}</small></div><ArrowRight size={15}/></div>) : <div className="empty-state"><Radar size={24}/><strong>No live opportunity events yet</strong><span>Events appear after connected sources report a material, evidence-backed change.</span></div>}
      </section>
      <section className="card source-overview">
        <div className="panel-title"><h2><Database size={17}/> Source coverage</h2><span>{providers.length} registered</span></div>
        {providers.slice(0, 7).map((provider) => <div className="source-row" key={provider.code}><div><strong>{provider.name}</strong><small>{provider.category} · Reliability {provider.reliability}</small></div><span className={provider.enabled ? "source-on" : "source-off"}>{provider.health.replaceAll("_", " ")}</span></div>)}
      </section>
    </div>
  </main>;
}
