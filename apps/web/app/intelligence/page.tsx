import HsIntelligenceHub from "@/components/HsIntelligenceHub";

export default function IntelligencePage() {
  return <main className="shell page catalog-page">
    <div className="eyebrow">HS 市场情报</div>
    <h1 className="page-title">全球 HS 市场情报</h1>
    <p className="subtitle">在同一个工作台中浏览全部六位 HS 市场分析，并跟踪原始数据下载、导入与计算进度。</p>
    <HsIntelligenceHub />
  </main>;
}
