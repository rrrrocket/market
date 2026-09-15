"use client";

import { ArrowRight, BarChart3, Database, Globe2, Layers3, Search, TrendingDown, TrendingUp } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { marketApi } from "@/lib/api";
import { DataQuality } from "@/types/market";

type Countries = Awaited<ReturnType<typeof marketApi.countryOpportunities>>;
type Catalog = Awaited<ReturnType<typeof marketApi.hsCatalog>>;
type Pipeline = Awaited<ReturnType<typeof marketApi.comtradePipeline>>;
type Product = Awaited<ReturnType<typeof marketApi.search>>[number];

const money = (value: number | null) => value == null ? "—" : new Intl.NumberFormat("zh-CN", {style:"currency",currency:"USD",notation:"compact",maximumFractionDigits:1}).format(value);
const percent = (value: number | null) => value == null ? "—" : `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;

export default function Home() {
  const [countries, setCountries] = useState<Countries | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [pipeline, setPipeline] = useState<Pipeline | null>(null);
  const [quality, setQuality] = useState<DataQuality | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [searchOpen, setSearchOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    Promise.all([
      marketApi.countryOpportunities(),
      marketApi.hsCatalog({status:"ALL",page:1,page_size:6}),
      marketApi.comtradePipeline(),
      marketApi.dataQuality(),
    ]).then(([countryData, catalogData, pipelineData, qualityData]) => {
      setCountries(countryData);
      setCatalog(catalogData);
      setPipeline(pipelineData);
      setQuality(qualityData);
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "首页数据加载失败"));
  }, []);

  useEffect(() => {
    const value = query.trim();
    if (value.length < 2) { setProducts([]); return; }
    const timer = window.setTimeout(() => marketApi.search(value).then((rows) => setProducts(rows.slice(0, 8))).catch(() => setProducts([])), 180);
    return () => window.clearTimeout(timer);
  }, [query]);

  async function submitSearch(event: FormEvent) {
    event.preventDefault();
    const value = query.trim();
    if (!value) return;
    const exact = products.find((product) => product.hs_code === value);
    const product = exact || products[0] || (await marketApi.search(value))[0];
    if (product) router.push(`/product/${product.hs_code}`);
  }

  if (error) return <main className="shell page"><section className="card error">{error}</section></main>;
  if (!countries || !catalog || !pipeline || !quality) return <main className="shell page"><section className="card loading">正在汇总全球市场数据…</section></main>;

  const readyProviders = quality.provider_health.filter((provider) => provider.status === "DATA_READY");
  const topCountries = countries.items.slice(0, 6);

  return <main className="shell market-dashboard">
    <section className="dashboard-hero">
      <div>
        <div className="eyebrow">Global market command center</div>
        <h1>全球市场机会总览</h1>
        <p>从中国出口数据出发，按国家与六位 HS 识别市场规模、增长趋势和未覆盖空间。</p>
      </div>
      <div className="dashboard-actions">
        <Link href="/countries" className="primary">查看国家机会 <ArrowRight size={16}/></Link>
        <Link href="/intelligence" className="secondary-action">HS Intelligence <ArrowRight size={16}/></Link>
      </div>
    </section>

    <form className="searchbox product-search dashboard-search" onSubmit={submitSearch}>
      <Search size={20} className="search-icon"/>
      <div className="search-field">
        <input aria-label="HS Code or product keyword" value={query} autoComplete="off" onChange={(event) => {setQuery(event.target.value);setSearchOpen(true);}} onFocus={() => setSearchOpen(true)} placeholder="输入 HS Code、英文或中文商品名称"/>
        {searchOpen && products.length > 0 && <div className="product-results">{products.map((product) => <button type="button" key={product.hs_code} onClick={() => router.push(`/product/${product.hs_code}`)}><strong>HS {product.hs_code}</strong><span>{product.name_en}</span><small>{product.name_zh || `${product.level}-digit HS 2022`}</small></button>)}</div>}
      </div>
      <button className="primary">分析全球市场 <ArrowRight size={16}/></button>
    </form>

    <section className="dashboard-kpis">
      <div className="card dashboard-kpi"><Globe2 size={18}/><span>覆盖国家/地区</span><strong>{countries.countries.toLocaleString()}</strong><small>{countries.year} 年优先口径</small></div>
      <div className="card dashboard-kpi"><Layers3 size={18}/><span>已分析 HS</span><strong>{catalog.summary.analyzed_hs.toLocaleString()}</strong><small>共 {catalog.summary.total_hs.toLocaleString()} 个六位 HS</small></div>
      <div className="card dashboard-kpi"><BarChart3 size={18}/><span>市场机会</span><strong>{(quality.coverage.opportunities ?? 0).toLocaleString()}</strong><small>HS × 国家分析结果</small></div>
      <div className="card dashboard-kpi"><Database size={18}/><span>贸易观察值</span><strong>{(quality.coverage.trade_observations ?? 0).toLocaleString()}</strong><small>{readyProviders.length} 个数据源已有数据</small></div>
    </section>

    <div className="dashboard-grid">
      <section className="card top-markets">
        <div className="panel-title"><h2>中国出口重点市场</h2><Link className="catalog-open" href="/countries">全部国家<ArrowRight size={14}/></Link></div>
        <div className="top-market-list">{topCountries.map((country) => <Link href={`/countries/${country.iso3}`} className="top-market-row" key={country.iso3}>
          <span className="ranknum">{country.rank.toString().padStart(2,"0")}</span>
          <div><strong>{country.name_zh || country.name}</strong><small>{country.name} · {country.iso3} · {country.hs_count.toLocaleString()} 个 HS</small></div>
          <div><small>自中国进口</small><strong>{money(country.china_import_value_usd)}</strong></div>
          <div className={(country.cagr_3y ?? 0) >= 0 ? "positive" : "negative"}>{(country.cagr_3y ?? 0) >= 0 ? <TrendingUp size={15}/> : <TrendingDown size={15}/>}<span>{percent(country.cagr_3y)}<small>3Y CAGR</small></span></div>
          <ArrowRight size={16}/>
        </Link>)}</div>
      </section>

      <aside className="card pipeline-overview">
        <div className="panel-title"><h2>全量分析进度</h2><Link className="catalog-open" href="/intelligence#pipeline">查看任务<ArrowRight size={14}/></Link></div>
        <div className="pipeline-body">
          <div className="pipeline-state"><span className={`quality-pill ${pipeline.status === "FAILED" ? "quality-warn" : "quality-good"}`}>{pipeline.status.replaceAll("_", " ")}</span><small>更新于 {pipeline.updated_at ? new Date(pipeline.updated_at).toLocaleString() : "—"}</small></div>
          {[["下载",pipeline.download_percent],["导入",pipeline.import_percent],["市场分析",pipeline.analysis_percent]].map(([label,value]) => <div className="pipeline-progress" key={String(label)}><div><span>{label}</span><strong>{Number(value).toFixed(1)}%</strong></div><div className="progress-track"><i style={{width:`${Math.min(100,Number(value))}%`}}/></div></div>)}
          <div className="pipeline-facts"><div><span>原始记录</span><strong>{pipeline.records_downloaded.toLocaleString()}</strong></div><div><span>完成批次</span><strong>{pipeline.imported_batches}/{pipeline.total_batches}</strong></div><div><span>当前 HS</span><strong>{pipeline.current_hs || "—"}</strong></div><div><span>失败 HS</span><strong>{pipeline.failed_hs.toLocaleString()}</strong></div></div>
        </div>
      </aside>
    </div>

    <section className="card dashboard-sources">
      <div className="panel-title"><h2>已进入分析的数据源</h2><Link className="catalog-open" href="/admin/data-quality">数据质量<ArrowRight size={14}/></Link></div>
      <div className="dashboard-source-grid">{readyProviders.map((provider) => <div key={provider.code}><Database size={17}/><span>{provider.name}</span><strong>{provider.record_count.toLocaleString()}</strong><small>{provider.category} · {provider.last_success_at ? new Date(provider.last_success_at).toLocaleDateString() : "—"}</small></div>)}</div>
    </section>
  </main>;
}
