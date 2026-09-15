"use client";

import { ArrowLeft, ArrowRight, Search, TrendingDown, TrendingUp } from "lucide-react";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { CountryOpportunityDetail, marketApi } from "@/lib/api";

const money = (value:number|null) => value == null ? "—" : new Intl.NumberFormat("zh-CN", {style:"currency",currency:"USD",notation:"compact",maximumFractionDigits:2}).format(value);
const percent = (value:number|null) => value == null ? "—" : `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;
const typeLabels:Record<string,string> = {FAST_GROWTH:"高速增长",WHITE_SPACE:"市场空白",SCALE_LEADER:"规模品类",EMERGING:"新兴机会",WATCH:"持续观察"};
const trendLabels:Record<string,string> = {FAST_GROWTH:"高速增长",ACCELERATING:"正在加速",GROWING:"持续增长",NEW:"新增进口",STABLE:"基本稳定",DECLINING:"近期下降"};
const macroLabels:Record<string,string> = {gdp_usd:"GDP",gdp_growth:"GDP 增长",gdp_per_capita:"人均 GDP",population:"人口",household_consumption:"居民消费",internet_penetration:"互联网渗透率",imports_percent_gdp:"进口占 GDP",trade_percent_gdp:"贸易占 GDP",urbanization:"城镇化率",inflation:"通胀率"};

function macroValue(key:string,value:number|null) {
  if (value == null) return "—";
  if (["gdp_growth","internet_penetration","imports_percent_gdp","trade_percent_gdp","urbanization","inflation"].includes(key)) return `${value.toFixed(1)}%`;
  if (["gdp_usd","gdp_per_capita","household_consumption"].includes(key)) return money(value);
  return new Intl.NumberFormat("zh-CN", {notation:"compact",maximumFractionDigits:1}).format(value);
}

function TrendChart({data}:{data:CountryOpportunityDetail["history"]}) {
  const points = useMemo(() => {
    const values = data.map((item) => item.china_import_value_usd ?? 0);
    const max = Math.max(...values, 1);
    return values.map((value,index) => ({
      x: data.length === 1 ? 50 : 7 + index * (86 / (data.length - 1)),
      y: 82 - value / max * 65,
      value,
      year:data[index].year,
    }));
  }, [data]);
  return <div className="country-trend-chart">
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="自中国进口趋势">
      <defs><linearGradient id="countryTrend" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1459d9" stopOpacity=".25"/><stop offset="1" stopColor="#1459d9" stopOpacity="0"/></linearGradient></defs>
      {[20,40,60,80].map((y) => <line key={y} x1="5" x2="95" y1={y} y2={y} className="chart-grid"/>)}
      {points.length > 1 && <polygon points={`7,82 ${points.map((point) => `${point.x},${point.y}`).join(" ")} 93,82`} fill="url(#countryTrend)"/>}
      <polyline points={points.map((point) => `${point.x},${point.y}`).join(" ")} className="trend-line"/>
      {points.map((point) => <circle key={point.year} cx={point.x} cy={point.y} r="1.8" className="trend-point"/>)}
    </svg>
    <div className="trend-axis">{points.map((point) => <span key={point.year}><b>{point.year}</b><small>{money(point.value)}</small></span>)}</div>
  </div>;
}

export default function CountryOpportunityDetailView({iso3}:{iso3:string}) {
  const [data, setData] = useState<CountryOpportunityDetail|null>(null);
  const [sort, setSort] = useState("opportunity");
  const [type, setType] = useState("");
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setData(await marketApi.countryOpportunity(iso3, {sort,q:search,opportunity_type:type,page,page_size:50})); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "无法加载国家分析"); }
    finally { setLoading(false); }
  }, [iso3, page, search, sort, type]);
  useEffect(() => { void load(); }, [load]);

  function submit(event:FormEvent) { event.preventDefault(); setPage(1); setSearch(query.trim()); }
  if (error) return <main className="shell page"><Link href="/countries" className="back-link"><ArrowLeft size={15}/>返回国家列表</Link><section className="card error">{error}</section></main>;
  if (!data) return <main className="shell page"><section className="card loading">正在加载国家分析…</section></main>;
  const summary = data.summary;
  const pages = Math.max(1, Math.ceil(data.product_pagination.total / data.product_pagination.page_size));
  return <main className="shell page country-detail-page">
    <Link href="/countries" className="back-link"><ArrowLeft size={15}/>返回国家列表</Link>
    <div className="country-detail-head">
      <div><div className="eyebrow">{data.country.region} · {data.country.iso3}</div><h1 className="page-title">{data.country.name_zh || data.country.name}</h1><p className="subtitle">{data.country.name} 从中国进口的 HS 商品排名与增长机会 · {data.year}</p></div>
      <div className="country-rank-note">数据口径 <strong>该国报告的自中国进口</strong><span>UN Comtrade · HS 6位</span></div>
    </div>
    <div className="country-summary-grid">
      <div className="card"><small>自中国进口总额</small><strong>{money(summary.china_import_value_usd)}</strong><span>{summary.imported_hs_count.toLocaleString()} 个 HS 有进口</span></div>
      <div className="card"><small>中国供应份额</small><strong>{summary.china_share == null ? "—" : `${(summary.china_share*100).toFixed(1)}%`}</strong><span>占该国这些品类总进口</span></div>
      <div className="card"><small>最新同比</small><strong className={(summary.yoy_growth ?? 0) >= 0 ? "positive" : "negative"}>{percent(summary.yoy_growth)}</strong><span>{data.year-1} → {data.year}</span></div>
      <div className="card"><small>三年复合增长</small><strong className={(summary.cagr_3y ?? 0) >= 0 ? "positive" : "negative"}>{percent(summary.cagr_3y)}</strong><span>{data.year-3} → {data.year}</span></div>
    </div>
    <section className="card country-history-card">
      <div className="chart-title"><div><h2>自中国进口趋势</h2><p>所有六位 HS 汇总；缺失年份保持为空。</p></div><strong>{money(summary.china_import_value_usd)}</strong></div>
      <TrendChart data={data.history}/>
    </section>
    <section className="card country-macro-card">
      <div className="panel-title"><h2>国家经营环境</h2><span>World Bank · 最新可用年份</span></div>
      {Object.keys(data.macro).length ? <div className="country-macro-grid">{Object.entries(data.macro).map(([key,item]) => <div key={key}><small>{macroLabels[key] || key.replaceAll("_"," ")}</small><strong>{macroValue(key,item.value)}</strong><span>{item.year} · {item.observed_type}</span></div>)}</div> : <div className="empty-state"><strong>尚未同步 World Bank 数据</strong><span>连接器可用，但当前国家没有已入库的宏观指标。</span></div>}
    </section>
    <section className="card catalog-table-card country-products">
      <div className="country-product-heading"><div><div className="eyebrow">HS 机会排名</div><h2>商品商业机会</h2></div><p>机会分数综合进口规模、增长、同比动量、市场空间和稳定性。</p></div>
      <div className="catalog-toolbar country-product-toolbar">
        <form onSubmit={submit}><Search size={17}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索 HS 或商品类目"/><button className="primary">搜索</button></form>
        <select value={type} onChange={(event) => {setType(event.target.value);setPage(1);}}><option value="">全部机会</option><option value="FAST_GROWTH">高速增长</option><option value="WHITE_SPACE">市场空白</option><option value="SCALE_LEADER">规模品类</option><option value="EMERGING">新兴机会</option><option value="WATCH">持续观察</option></select>
        <select value={sort} onChange={(event) => {setSort(event.target.value);setPage(1);}}><option value="opportunity">按机会分数</option><option value="china_import">按对华进口额</option><option value="growth">按三年增长</option><option value="headroom">按市场空间</option></select>
      </div>
      {loading && <div className="loading table-loading">正在更新排名…</div>}
      {!loading && <div className="catalog-scroll"><table className="table product-opportunity-table">
        <thead><tr><th>机会排名</th><th>HS / 商品</th><th>机会类型</th><th>自中国进口</th><th>进口排名</th><th>同比</th><th>三年 CAGR</th><th>中国份额</th><th>机会分</th><th></th></tr></thead>
        <tbody>{data.products.map((item) => <tr key={item.hs_code}>
          <td className="ranknum">{item.opportunity_rank.toString().padStart(2,"0")}</td>
          <td><code>{item.hs_code}</code><strong>{item.name_en}</strong>{item.name_zh && <small>{item.name_zh}</small>}</td>
          <td><span className={`opportunity-type type-${item.opportunity_type.toLowerCase()}`}>{typeLabels[item.opportunity_type]}</span><small className="trend-label">{trendLabels[item.trend]}</small></td>
          <td><strong>{money(item.china_import_value_usd)}</strong><small>空间 {money(item.unserved_value_usd)}</small></td>
          <td>{item.china_import_rank ? `#${item.china_import_rank}` : "—"}</td>
          <td className={(item.yoy_growth ?? 0)>=0?"positive":"negative"}>{(item.yoy_growth ?? 0)>=0?<TrendingUp size={14}/>:<TrendingDown size={14}/>} {percent(item.yoy_growth)}</td>
          <td className={(item.cagr_3y ?? 0)>=0?"positive":"negative"}>{percent(item.cagr_3y)}</td>
          <td>{item.china_share == null ? "—" : `${(item.china_share*100).toFixed(1)}%`}</td>
          <td><span className="opportunity-score">{item.opportunity_score.toFixed(1)}</span></td>
          <td><Link className="catalog-open" href={`/product/${item.hs_code}/country/${data.country.iso3}`}>查看该市场<ArrowRight size={14}/></Link></td>
        </tr>)}</tbody>
      </table></div>}
      <div className="catalog-pagination"><span>第 {page} / {pages} 页 · {data.product_pagination.total.toLocaleString()} 个 HS</span><div><button disabled={page<=1} onClick={() => setPage((value)=>value-1)}><ArrowLeft size={15}/></button><button disabled={page>=pages} onClick={() => setPage((value)=>value+1)}><ArrowRight size={15}/></button></div></div>
    </section>
  </main>;
}
