"use client";

import { useEffect, useState } from "react";
import { marketApi } from "@/lib/api";

export default function ProductHeading({ hsCode }: { hsCode: string }) {
  const [name, setName] = useState("正在加载 HS 类目…");
  useEffect(() => {
    marketApi.search(hsCode).then((products) => {
      const product = products.find((item) => item.hs_code === hsCode);
      setName(product?.name_zh || product?.name_en || "未知 HS 类目");
    }).catch(() => setName("未知 HS 类目"));
  }, [hsCode]);
  return <><div className="eyebrow">HS {hsCode}</div><h1 className="page-title">{name}</h1><p className="subtitle">HS 2022 · 全球市场情报 · 原产地中国 · 可解释市场评分</p></>;
}
