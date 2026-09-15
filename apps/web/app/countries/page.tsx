import CountryOpportunityExplorer from "@/components/CountryOpportunityExplorer";

export default function CountriesPage() {
  return <main className="shell page country-page">
    <div className="eyebrow">国家 → HS 商业机会</div>
    <h1 className="page-title">国家商业机会</h1>
    <p className="subtitle">从国家视角查看自中国进口规模、增长趋势和覆盖的 HS 数量，并进入各国查看商品机会排名。</p>
    <CountryOpportunityExplorer />
  </main>;
}
