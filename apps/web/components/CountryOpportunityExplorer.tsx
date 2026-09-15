"use client";

import { ArrowRight, Search, TrendingDown, TrendingUp } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { CountryOpportunityItem, marketApi } from "@/lib/api";

const money = (value:number|null) => value == null ? "—" : new Intl.NumberFormat("zh-CN", {style:"currency",currency:"USD",notation:"compact",maximumFractionDigits:1}).format(value);
const percent = (value:number|null) => value == null ? "—" : `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;

export default function CountryOpportunityExplorer() {
  const [items, setItems] = useState<CountryOpportunityItem[]>([]);
  const [total, setTotal] = useState(0);
  const [year, setYear] = useState(0);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("value");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    marketApi.countryOpportunities().then((data) => {
      setItems(data.items); setTotal(data.total_china_import_value_usd); setYear(data.year);
    }).catch((reason) => setError(reason instanceof Error ? reason.message : "Country data unavailable"))
      .finally(() => setLoading(false));
  }, []);

  const visible = useMemo(() => {
    const term = query.trim().toLowerCase();
    const rows = items.filter((item) => !term || item.iso3.toLowerCase().includes(term) || item.name.toLowerCase().includes(term) || item.name_zh?.includes(term));
    return [...rows].sort((a,b) => {
      if (sort === "growth") return (b.cagr_3y ?? -Infinity) - (a.cagr_3y ?? -Infinity);
      if (sort === "share") return (b.china_share ?? -Infinity) - (a.china_share ?? -Infinity);
      return (b.china_import_value_usd ?? -Infinity) - (a.china_import_value_usd ?? -Infinity);
    });
  }, [items, query, sort]);

  if (loading) return <section className="card loading">Loading country opportunities…</section>;
  if (error) return <section className="card error">{error}</section>;
  const growing = items.filter((item) => (item.cagr_3y ?? 0) > 0).length;
  return <>
    <div className="catalog-stats country-stats">
      <div className="card"><small>覆盖国家/地区</small><strong>{items.length}</strong></div>
      <div className="card"><small>各地最新自中国进口</small><strong>{money(total)}</strong></div>
      <div className="card"><small>三年保持增长</small><strong>{growing}</strong></div>
      <div className="card"><small>分析口径</small><strong>HS 6位</strong></div>
    </div>
    <section className="card catalog-table-card">
      <div className="catalog-toolbar">
        <div className="country-search"><Search size={17}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索国家、地区或 ISO3"/></div>
        <select value={sort} onChange={(event) => setSort(event.target.value)}>
          <option value="value">按对华进口额</option><option value="growth">按三年增长</option><option value="share">按中国份额</option>
        </select>
      </div>
      <div className="catalog-scroll"><table className="table country-table">
        <thead><tr><th>排名</th><th>国家/地区</th><th>自中国进口</th><th>中国份额</th><th>同比</th><th>三年 CAGR</th><th>进口 HS</th><th></th></tr></thead>
        <tbody>{visible.map((item) => <tr key={item.iso3}>
          <td className="ranknum">{item.rank.toString().padStart(2,"0")}</td>
          <td><strong>{item.name}</strong><small>{item.name_zh || item.region || item.iso3} · {item.iso3} · 数据 {item.year}</small></td>
          <td><strong>{money(item.china_import_value_usd)}</strong></td>
          <td>{item.china_share == null ? "—" : `${(item.china_share * 100).toFixed(1)}%`}</td>
          <td className={(item.yoy_growth ?? 0) >= 0 ? "positive" : "negative"}>{(item.yoy_growth ?? 0) >= 0 ? <TrendingUp size={14}/> : <TrendingDown size={14}/>} {percent(item.yoy_growth)}</td>
          <td className={(item.cagr_3y ?? 0) >= 0 ? "positive" : "negative"}>{percent(item.cagr_3y)}</td>
          <td>{item.imported_hs_count.toLocaleString()}</td>
          <td><Link className="catalog-open" href={`/countries/${item.iso3}`}>查看机会<ArrowRight size={14}/></Link></td>
        </tr>)}</tbody>
      </table></div>
    </section>
    <p className="catalog-note">优先使用 {year} 年；未报送该年度的国家/地区自动使用其截至 {year} 的最新可用年度，年份已逐行标注。</p>
  </>;
}
