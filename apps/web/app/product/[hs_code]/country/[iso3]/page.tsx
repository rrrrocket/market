import CountryDetail from "@/components/CountryDetail";
export default async function CountryPage({params}:{params:Promise<{hs_code:string;iso3:string}>}){const {hs_code,iso3}=await params;return <main className="shell page"><CountryDetail hs={hs_code} iso3={iso3.toUpperCase()}/></main>}

