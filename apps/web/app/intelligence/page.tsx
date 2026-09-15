import ComtradePipelineDashboard from "@/components/ComtradePipelineDashboard";
import HsAnalysisCatalog from "@/components/HsAnalysisCatalog";

export default function IntelligencePage() {
  return <main className="shell page catalog-page">
    <div className="eyebrow">All HS market intelligence</div>
    <h1 className="page-title">全球 HS 市场分析</h1>
    <p className="subtitle">原始贸易数据先保存到本地，再生成每个六位 HS 对应的全球市场规模、增长、趋势和中国份额排名。</p>
    <ComtradePipelineDashboard />
    <HsAnalysisCatalog />
  </main>;
}
