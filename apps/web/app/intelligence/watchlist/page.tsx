import WatchlistDashboard from "@/components/WatchlistDashboard";

export default function WatchlistPage() {
  return <main className="shell page">
    <div className="eyebrow">市场监测</div>
    <h1 className="page-title">观察清单</h1>
    <p className="subtitle">持续监测商品、国家和渠道组合，在新证据出现时追踪变化。</p>
    <WatchlistDashboard />
  </main>;
}
