"use client";

import { useEffect, useState } from "react";
import { marketApi } from "@/lib/api";

export default function ProductHeading({ hsCode }: { hsCode: string }) {
  const [name, setName] = useState("Loading HS category…");
  useEffect(() => {
    marketApi.search(hsCode).then((products) => {
      setName(products.find((product) => product.hs_code === hsCode)?.name_en || "Unknown HS category");
    }).catch(() => setName("Unknown HS category"));
  }, [hsCode]);
  return <><div className="eyebrow">HS {hsCode}</div><h1 className="page-title">{name}</h1><p className="subtitle">HS 2022 · Global market intelligence · Origin China · Explainable market score</p></>;
}
