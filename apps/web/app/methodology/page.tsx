const semantics = [
  ["已报告（REPORTED）", "政府、企业或供应商正式发布的数据。"],
  ["已观测（OBSERVED）", "Matrix One 通过 API 或公开页面直接观测到的状态。"],
  ["估算（ESTIMATED）", "由统计模型估算，不属于直接观测值。"],
  ["推导（INFERRED）", "由规则综合多项已有信号得出的结论。"],
  ["AI 生成（AI_GENERATED）", "由 AI 生成的文字或假设；必须关联证据，否则只能视为假设。"],
];

export default function Methodology() {
  return <main className="shell page method">
    <div className="eyebrow">透明、可追溯的分析</div>
    <h1 className="page-title">分析方法与数据可靠性</h1>
    <p className="subtitle">说明事实数据如何转化为信号、置信度和决策依据，并确保缺失数据不会被包装成确定结论。</p>

    <section className="card"><h2>数据处理流程</h2><div className="method-flow"><span>原始快照</span><b>→</b><span>标准化记录</span><b>→</b><span>需求信号</span><b>→</b><span>市场机会</span><b>→</b><span>决策</span></div><p>数据源原始响应保持不可变；标准化数据和衍生情报均关联来源、获取时间、版本与证据。</p></section>

    <section className="card"><h2>数据观测类型</h2><div className="semantic-grid">{semantics.map(([label, copy]) => <div key={label}><strong>{label}</strong><p>{copy}</p></div>)}</div></section>

    <section className="card"><h2>数据源可靠性</h2><p>可靠性是数据源层面的元数据，可由管理员调整；高可靠性并不表示该来源的每一个数值都绝对正确。</p><div className="reliability-scale"><span>A+<small>已验证的 Matrix One 业务结果</small></span><span>A<small>官方统计与已确认报价</small></span><span>A−<small>官方市场或采购 API</small></span><span>B+/B<small>官方行为信号与公开观测</small></span><span>C<small>第三方估算</small></span><span>D<small>较弱或 AI 推导来源</small></span></div></section>

    <section className="card"><h2>市场吸引力</h2><p>当前可复现评分用于比较商品—国家组合的结构性需求，不是销售额、利润或分销结果预测。</p><div className="formula">市场吸引力 = 45% 市场规模 + 30% 结构增长 + 15% 增长动量 + 10% 稳定性</div><p>缺失项不会按零分处理。系统会按已有指标重新归一化权重，同时用数据覆盖度说明原公式中实际可计算的比例。</p></section>

    <section className="card"><h2>分销机会</h2><p>只有在中国供给匹配度和经济性数据均经过验证后，才会生成该分数；单独的需求数据不能直接构成分销建议。</p><div className="formula">需求 30% · 供给匹配 25% · 经济性 20% · 竞争 10% · 市场准入 10% · 风险 5%</div></section>

    <section className="card"><h2>置信度独立计算</h2><div className="formula">置信度 = 35% 覆盖度 + 30% 可靠性 + 20% 时效性 + 15% 跨来源一致性</div><p>置信度描述结论背后的证据质量，不表示市场吸引力或商业收益大小。</p></section>

    <section className="card"><h2>数据时效性</h2><p>不同数据采用不同老化规则：年度贸易和宏观数据按月计算，月度贸易按周计算，市场平台、招标和供应商数据按小时或天计算；无法判断时效性时保持“未知”。</p></section>

    <section className="card"><h2>已知限制</h2><p>贸易数据可能存在修订、镜像数据差异、转口贸易、申报缺口和 HS 分类变更。单位价值是海关货值除以数量或重量，不等同于零售价。Google Trends 接入后代表归一化关注度，而不是绝对搜索量。</p><p>评分定义保持不可变；公式调整会创建新的评分版本，历史结果仍可复现。</p></section>
  </main>;
}
