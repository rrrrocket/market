import MarketWorkspace from "@/components/MarketWorkspace";
import ProductHeading from "@/components/ProductHeading";
export default async function ProductPage({params}:{params:Promise<{hs_code:string}>}){const {hs_code}=await params;return <main className="shell page"><ProductHeading hsCode={hs_code}/><MarketWorkspace initialHs={hs_code} heading={false}/></main>}
