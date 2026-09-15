import CountryOpportunityDetailView from "@/components/CountryOpportunityDetail";

export default async function CountryPage({params}:{params:Promise<{iso3:string}>}) {
  const {iso3} = await params;
  return <CountryOpportunityDetailView iso3={iso3.toUpperCase()} />;
}
