import DataQualityDashboard from "@/components/DataQualityDashboard";

export default function DataQualityPage() {
  return <main className="shell page">
    <div className="eyebrow">Admin · Data governance</div>
    <h1 className="page-title">Data quality</h1>
    <p className="subtitle">Provider health, provenance coverage, freshness, and confidence gaps.</p>
    <DataQualityDashboard />
  </main>;
}
