"use client";

import { Database, Info, RefreshCw, ShieldAlert, Store, Truck } from "lucide-react";
import { useEffect, useState } from "react";

import { marketApi } from "@/lib/api";
import { label } from "@/lib/labels";
import { Detail, Opportunity } from "@/types/market";
import TrendChart from "./TrendChart";

const pct = (value: number | null) => value === null ? "—" : `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;
const score = (value: number | null) => value === null ? "暂无数据" : value.toFixed(0);
const money = (value:number|null,currency="USD") => {
  if (value === null) return "—";
  try { return new Intl.NumberFormat("zh-CN", {style:"currency",currency,notation:"compact",maximumFractionDigits:1}).format(value); }
  catch { return `${new Intl.NumberFormat("zh-CN", {notation:"compact",maximumFractionDigits:1}).format(value)} ${currency}`; }
};
const layerLabels: Record<string,string> = {STRUCTURAL:"结构需求",DIGITAL:"数字需求",MARKETPLACE:"市场平台",EXPLICIT:"显性需求"};

function ScoreCard({title, value, state}:{title:string;value:number|null;state?:string}) {
  return <div className={`score-card ${value === null ? "score-card-empty" : ""}`}><span>{title}</span><strong>{score(value)}</strong><small>{value === null ? state || "未接入" : "0–100"}</small></div>;
}

export default function CountryDetail({hs, iso3}:{hs:string;iso3:string}) {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [suppliers, setSuppliers] = useState<{supplier_iso3:string;supplier_name:string;trade_value_usd:number;share:number;rank:number}[]>([]);
  const [productName, setProductName] = useState(`HS ${hs}`);
  const [error, setError] = useState("");
  const [enrichment, setEnrichment] = useState("");

  useEffect(() => {
    (async () => {
      try {
        marketApi.search(hs).then((products) => {
          const exact = products.find((product) => product.hs_code === hs);
          if (exact) setProductName(exact.name_zh || exact.name_en);
        }).catch(() => undefined);
        let rows = await marketApi.opportunities(hs);
        if (!rows.length) {
          const run = await marketApi.createAnalysis(hs);
          for (let index = 0; index < 20; index += 1) {
            await new Promise((resolve) => setTimeout(resolve, 500));
            const status = await marketApi.analysis(run.id);
            if (status.status === "COMPLETED") break;
          }
          rows = await marketApi.opportunities(hs);
        }
        const item = rows.find((row: Opportunity) => row.destination_iso3 === iso3);
        if (!item) throw new Error("当前分析中没有该国家/地区");
        const full = await marketApi.detail(item.id);
        setDetail(full);
        setSuppliers(await marketApi.suppliers(hs, iso3, full.period_year));
      } catch (reason: unknown) {
        setError(reason instanceof Error ? reason.message : "无法加载市场机会");
      }
    })();
  }, [hs, iso3]);

  if (error) return <div className="card error">{error}</div>;
  if (!detail) return <div className="card loading">正在加载市场机会证据…</div>;
  const currentDetail = detail;

  async function enrich() {
    setEnrichment("正在同步 World Bank、WITS 和 TED…");
    const results = await Promise.allSettled([
      marketApi.syncWorldBank([iso3]),
      marketApi.syncWits(hs, iso3, currentDetail.period_year),
      marketApi.syncTed(hs, iso3, productName),
    ]);
    const completed = results.filter((item) => item.status === "fulfilled").length;
    setEnrichment(`已同步 ${completed}/3 个数据源，正在刷新…`);
    window.setTimeout(() => window.location.reload(), 700);
  }

  return <>
    <div className="opportunity-heading">
      <div><div className="eyebrow">{productName} · {iso3}</div><h1 className="page-title">{detail.country_name}</h1><p className="subtitle">HS {hs} · 全部渠道 · {detail.period_year}</p></div>
      <div className="opportunity-actions"><button className="secondary-action" onClick={enrich} disabled={Boolean(enrichment)}><RefreshCw size={14} className={enrichment ? "spin" : ""}/>{enrichment || "同步外部数据"}</button><div className="confidence-badge"><span>置信度</span><strong>{detail.scores.confidence?.toFixed(0) ?? "—"}</strong><small>{label(detail.confidence_label)}</small></div></div>
    </div>

    <section className="score-surface card">
      <div className="score-primary"><span>{detail.scores.distribution_opportunity === null ? "市场吸引力" : "分销机会"}</span><strong>{score(detail.scores.distribution_opportunity ?? detail.scores.market_attractiveness)}</strong><small>{detail.scores.distribution_opportunity === null ? "供给与经济性接入后才能生成完整机会分。" : "决策评分"}</small></div>
      <div className="score-grid">
        <ScoreCard title="结构需求" value={detail.scores.structural_demand}/><ScoreCard title="数字需求" value={detail.scores.digital_demand}/><ScoreCard title="市场平台" value={detail.scores.marketplace_demand}/><ScoreCard title="显性需求" value={detail.scores.explicit_demand}/><ScoreCard title="供给匹配" value={detail.scores.supply_fit}/><ScoreCard title="经济性" value={detail.scores.economics} state="数据不足"/><ScoreCard title="市场准入" value={detail.scores.market_access}/><ScoreCard title="风险" value={detail.scores.risk} state="未知"/>
      </div>
    </section>

    <div className="detail-grid">
      <section className="card insight"><div className="section-label">为什么选择该市场？</div><ul className="reasons">{detail.reasons.map((reason, index) => <li key={index}><b className={reason.sentiment === "negative" ? "negative" : ""}>{reason.sentiment === "negative" ? "−" : "+"}</b>{reason.text}</li>)}</ul><p className="provenance-note">仅依据已关联证据生成，不构成销售预测。</p></section>
      <section className="card"><div className="panel-title"><h2>需求层</h2><span>数据连接状态</span></div><div className="layer-list">{Object.keys(layerLabels).map((layer) => <div key={layer}><span>{layerLabels[layer]}</span><strong>{detail.signals[layer]?.length ? `${detail.signals[layer].length} 条信号` : "暂无接入数据"}</strong></div>)}</div></section>
    </div>

    <div className="section-grid detail-sections">
      <section className="card chart-card"><div className="chart-title"><div><h2>结构性贸易需求</h2><p>进口国报告数据 · 最近五个完整年度</p></div></div><TrendChart history={detail.history}/></section>
      <section className="card"><div className="panel-title"><h2>供应来源国</h2><span>占目的国进口份额</span></div><table className="table"><tbody>{suppliers.slice(0, 6).map((supplier) => <tr key={supplier.supplier_iso3}><td>#{supplier.rank}</td><td><strong>{supplier.supplier_name}</strong><small>{supplier.supplier_iso3}</small></td><td><div className="bar"><i style={{width:`${Math.min(100, supplier.share * 100)}%`}}/></div></td><td>{(supplier.share * 100).toFixed(1)}%</td></tr>)}</tbody></table></section>
      <section className="card intelligence-block"><div className="block-icon"><Store size={19}/></div><div><h2>中国供给</h2><strong>{detail.supply.status === "CONNECTED" ? "已接入" : "未接入"}</strong><p>接入 Supplier Network API 后显示供应商数量、报价、成本、MOQ、库存、交期和能力。</p></div></section>
      <section className="card intelligence-block"><div className="block-icon"><Truck size={19}/></div><div><h2>经济性</h2><strong>{detail.economics.status === "AVAILABLE" ? "可用" : "数据不足"}</strong><p>完税成本、渠道费用、贡献毛利和盈亏平衡价格仅在输入经过验证后显示。</p></div></section>
      <section className="card intelligence-block"><div className="block-icon"><ShieldAlert size={19}/></div><div><h2>市场准入与关税</h2><strong>{detail.market_access ? `中国适用税率 ${detail.market_access.china_applicable_tariff?.toFixed(2) ?? "—"}%` : "尚未同步"}</strong><p>{detail.market_access ? `最惠国税率 ${detail.market_access.mfn_tariff?.toFixed(2) ?? "—"}% · ${detail.market_access.period_year} · ${label(detail.market_access.observed_type)}` : "点击“同步外部数据”获取该 HS 与目的国的 WITS / UNCTAD TRAINS 报告税率。"}</p></div></section>
      <section className="card intelligence-block"><div className="block-icon"><Info size={19}/></div><div><h2>中国市场位置</h2><strong>{pct(detail.china_share)}</strong><p>目的国报告的自中国进口份额，不代表供给匹配评分。</p></div></section>
      <section className="card intelligence-block"><div className="block-icon"><Database size={19}/></div><div><h2>国家承载能力</h2><strong>{detail.macro.gdp_usd ? money(detail.macro.gdp_usd.value) : "尚未同步"}</strong><p>{detail.macro.gdp_per_capita ? `人均 GDP ${money(detail.macro.gdp_per_capita.value)} · ${detail.macro.gdp_per_capita.year}` : "同步后显示 World Bank GDP、消费、人口和互联网普及指标。"}</p></div></section>
    </div>

    <section className="card evidence-section"><div className="panel-title"><h2>已观测公开招标</h2><span>TED EU · 匹配 {detail.explicit_demands.length} 条</span></div>{detail.explicit_demands.length ? <div className="table-wrap"><table className="table"><thead><tr><th>发布日期</th><th>采购方</th><th>招标项目</th><th>预算</th><th>状态</th></tr></thead><tbody>{detail.explicit_demands.map((tender) => <tr key={tender.id}><td>{new Date(tender.published_at).toLocaleDateString()}</td><td>{tender.buyer_name || "—"}</td><td>{tender.source_url ? <a className="catalog-open" href={tender.source_url} target="_blank" rel="noreferrer">{tender.title}</a> : tender.title}</td><td>{money(tender.budget_max,tender.currency || "EUR")}</td><td>{label(tender.status)}</td></tr>)}</tbody></table></div> : <div className="empty-state"><strong>暂无匹配的招标记录</strong><span>同步当前市场后，系统会使用已登记的 HS 商品描述搜索 TED 有效公告。</span></div>}</section>

    <section className="card evidence-section"><div className="panel-title"><h2><Database size={17}/> 证据清单</h2><span>{detail.evidence.length} 条关联事实</span></div><div className="table-wrap"><table className="table"><thead><tr><th>指标</th><th>数值</th><th>来源</th><th>类型</th><th>可靠性</th><th>期间</th><th>获取日期</th></tr></thead><tbody>{detail.evidence.map((evidence) => <tr key={`${evidence.id}-${evidence.metric_key}`}><td>{label(evidence.metric_key)}</td><td><strong>{evidence.display_value}</strong></td><td>{evidence.source_identifier}{evidence.notes && <small>{evidence.notes}</small>}</td><td><span className="data-badge">{label(evidence.observed_type || "REPORTED")}</span></td><td>{evidence.source_reliability || "A"}</td><td>{evidence.period}</td><td>{new Date(evidence.retrieved_at).toLocaleDateString()}</td></tr>)}</tbody></table></div></section>
  </>;
}
