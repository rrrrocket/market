import DataQualityDashboard from "@/components/DataQualityDashboard";

export default function DataQualityPage() {
  return <main className="shell page">
    <div className="eyebrow">管理 · 数据治理</div>
    <h1 className="page-title">数据质量</h1>
    <p className="subtitle">查看数据源健康状态、来源覆盖、时效性和置信度缺口。</p>
    <DataQualityDashboard />
  </main>;
}
