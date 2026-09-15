import HsAnalysisCatalog from "@/components/HsAnalysisCatalog";

export default function CatalogPage() {
  return <main className="shell page catalog-page">
    <div className="eyebrow">All HS market intelligence</div>
    <h1 className="page-title">全球 HS 市场分析库</h1>
    <p className="subtitle">覆盖全部六位 HS 商品；已完成的条目可直接查看国家排名，未完成的条目明确显示数据状态。</p>
    <HsAnalysisCatalog />
  </main>;
}
