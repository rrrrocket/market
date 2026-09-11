import WatchlistDashboard from "@/components/WatchlistDashboard";

export default function WatchlistPage() {
  return <main className="shell page">
    <div className="eyebrow">Intelligence</div>
    <h1 className="page-title">Watchlist</h1>
    <p className="subtitle">Monitor product, market, and channel combinations as new evidence arrives.</p>
    <WatchlistDashboard />
  </main>;
}
