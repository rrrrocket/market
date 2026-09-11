import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import "./enhancements.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://market.matrix-one.tech"),
  title: "Matrix One Market",
  description: "Explainable global demand intelligence for Chinese products",
};
export default function RootLayout({children}:{children:React.ReactNode}) {
  return <html lang="en"><body>
    <header className="topbar"><div className="shell nav">
      <Link href="/" className="brand"><span className="brandmark">M</span><span>Matrix One <span style={{fontWeight:500,color:"#738197"}}>Market</span></span></Link>
      <nav className="navlinks" aria-label="Primary navigation">
        <Link href="/">Overview</Link>
        <Link href="/explore">Discover</Link>
        <Link href="/intelligence/watchlist">Watchlist</Link>
        <Link href="/admin/data-quality">Data Quality</Link>
        <Link href="/methodology">Methodology</Link>
      </nav>
    </div></header>
    {children}
  </body></html>;
}
