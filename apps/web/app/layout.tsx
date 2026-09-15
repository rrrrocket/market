import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import "./enhancements.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://market.matrix-one.tech"),
  title: "Matrix One Market",
  description: "面向中国商品的可解释全球市场情报",
};
export default function RootLayout({children}:{children:React.ReactNode}) {
  return <html lang="en"><body>
    <header className="topbar"><div className="shell nav">
      <Link href="/" className="brand"><span className="brandmark">M</span><span>Matrix One <span style={{fontWeight:500,color:"#738197"}}>Market</span></span></Link>
      <nav className="navlinks" aria-label="主导航">
        <Link href="/">总览</Link>
        <Link href="/intelligence">HS 市场情报</Link>
        <Link href="/countries">国家机会</Link>
        <Link href="/intelligence/watchlist">观察清单</Link>
        <Link href="/admin/data-quality">数据质量</Link>
        <Link href="/methodology">方法说明</Link>
      </nav>
    </div></header>
    {children}
  </body></html>;
}
