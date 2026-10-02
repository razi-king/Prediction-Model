"use client";

/** Output 5: what-if boosts — "if you learned X, the models predict ...". */
export default function WhatIfList({ boosts }) {
  return (
    <div className="card">
      <div className="card-title">What-if boosts</div>
      <div className="card-sub">We add one skill to your profile, re-run both models, and measure the change</div>
      {boosts.length === 0 ? (
        <p className="hint">No single skill gives a measurable boost for this profile.</p>
      ) : (
        <div className="table-wrap">
          <table className="boosts">
            <thead>
              <tr><th>Learn</th><th>Market value</th><th>Level score</th><th>Reach goal</th></tr>
            </thead>
            <tbody>
              {boosts.map((b) => (
                <tr key={b.skill}>
                  <td className="skill">{b.skill}</td>
                  <td className={b.salary_boost_pct > 0 ? "up" : ""}>{b.salary_boost_pct > 0 ? "+" : ""}{b.salary_boost_pct.toFixed(1)}%</td>
                  <td>{b.score_boost > 0 ? "+" : ""}{b.score_boost.toFixed(1)}</td>
                  <td>{b.months_sooner > 0 ? <span className="up">{b.months_sooner} mo sooner</span> : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
