"use client";

import { Database, ListTree } from "lucide-react";
import { useEffect, useState } from "react";

import ComtradePipelineDashboard from "./ComtradePipelineDashboard";
import HsAnalysisCatalog from "./HsAnalysisCatalog";

type View = "catalog" | "pipeline";

export default function HsIntelligenceHub() {
  const [view, setView] = useState<View>("catalog");

  useEffect(() => {
    const syncHash = () => setView(window.location.hash === "#pipeline" ? "pipeline" : "catalog");
    syncHash();
    window.addEventListener("hashchange", syncHash);
    return () => window.removeEventListener("hashchange", syncHash);
  }, []);

  function select(next: View) {
    setView(next);
    window.history.replaceState(null, "", next === "pipeline" ? "#pipeline" : window.location.pathname);
  }

  return <>
    <div className="intelligence-tabs" role="tablist" aria-label="HS 市场情报视图">
      <button role="tab" aria-selected={view === "catalog"} className={view === "catalog" ? "active" : ""} onClick={() => select("catalog")}><ListTree size={17}/><span>市场分析库<small>浏览全部六位 HS 与市场结果</small></span></button>
      <button role="tab" aria-selected={view === "pipeline"} className={view === "pipeline" ? "active" : ""} onClick={() => select("pipeline")}><Database size={17}/><span>数据处理任务<small>下载、导入与分析进度</small></span></button>
    </div>
    <div role="tabpanel">{view === "catalog" ? <HsAnalysisCatalog/> : <ComtradePipelineDashboard/>}</div>
  </>;
}
