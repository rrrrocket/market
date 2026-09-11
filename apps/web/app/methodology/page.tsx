const semantics = [
  ["REPORTED", "A government, company, or supplier formally reported the value."],
  ["OBSERVED", "Matrix One directly observed a state through an API or public surface."],
  ["ESTIMATED", "A statistical model estimated the value; it is not a direct observation."],
  ["INFERRED", "A rule combined multiple recorded signals into a conclusion."],
  ["AI_GENERATED", "AI produced text or a hypothesis. It must link evidence or remain a hypothesis."],
];

export default function Methodology() {
  return <main className="shell page method">
    <div className="eyebrow">Transparent by design</div>
    <h1 className="page-title">Methodology & data reliability</h1>
    <p className="subtitle">How recorded facts become signals, confidence, and decision support without turning missing data into invented certainty.</p>

    <section className="card"><h2>Data pipeline</h2><div className="method-flow"><span>Raw snapshot</span><b>→</b><span>Canonical observation</span><b>→</b><span>Demand signal</span><b>→</b><span>Opportunity</span><b>→</b><span>Decision</span></div><p>Raw provider responses remain immutable. Normalized records and derived intelligence link back to their source, retrieval time, version, and evidence.</p></section>

    <section className="card"><h2>Observed type</h2><div className="semantic-grid">{semantics.map(([label, copy]) => <div key={label}><strong>{label}</strong><p>{copy}</p></div>)}</div></section>

    <section className="card"><h2>Source reliability</h2><p>Reliability is source metadata and can be adjusted by administrators. It does not make every value from a source correct.</p><div className="reliability-scale"><span>A+<small>Verified Matrix One outcomes</small></span><span>A<small>Official statistics and confirmed offers</small></span><span>A−<small>Official marketplace APIs</small></span><span>B+/B<small>Official behavior signals and public observations</small></span><span>C<small>Third-party estimates</small></span><span>D<small>Weak or AI-inferred sources</small></span></div></section>

    <section className="card"><h2>Market Attractiveness</h2><p>The current reproducible score ranks product-country structural demand. It is not a sales, profit, or distribution forecast.</p><div className="formula">Market Attractiveness = 45% Size + 30% Structural Growth + 15% Momentum + 10% Stability</div><p>Missing components are not zero. Available weights are re-normalized, while Coverage shows how much of the intended formula was available.</p></section>

    <section className="card"><h2>Distribution Opportunity</h2><p>This score remains <strong>Not enough data</strong> until both verified China Supply Fit and Economics are available. Demand alone cannot become a distribution recommendation.</p><div className="formula">Demand 30% · Supply Fit 25% · Economics 20% · Competition 10% · Market Access 10% · Risk 5%</div></section>

    <section className="card"><h2>Confidence is separate</h2><div className="formula">Confidence = 35% Coverage + 30% Reliability + 20% Freshness + 15% Cross-source Consistency</div><p>Confidence describes the evidence supporting an output; it does not describe market attractiveness or commercial upside.</p></section>

    <section className="card"><h2>Freshness</h2><p>Freshness rules follow the data type: annual trade and macro data age over months, monthly trade over weeks, and marketplace, tender, and supplier data over hours or days. Unknown freshness remains UNKNOWN.</p></section>

    <section className="card"><h2>Known limitations</h2><p>Trade data can include revisions, mirror-data differences, re-exports, reporting gaps, and HS classification changes. Unit value is customs value divided by quantity or weight; it is not a retail price. Google Trends, when connected, represents normalized interest rather than absolute search volume.</p><p>Score definitions are immutable. Formula changes create a new score version while earlier results remain reproducible.</p></section>
  </main>;
}
