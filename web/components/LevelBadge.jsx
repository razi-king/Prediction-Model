"use client";

import { formatMoney, LEVEL_COLORS } from "@/lib/api";

/** Output 1: current level + 0-100 score ring + market value + probability of each level. */
export default function LevelBadge({ result, levels }) {
  const idx = levels.indexOf(result.level);
  const r = 56;
  const circumference = 2 * Math.PI * r;
  const filled = (result.score / 100) * circumference;

  return (
    <div className="card">
      <div className="grid-2" style={{ alignItems: "center" }}>
        <div className="level-hero">
          <div className="level-ring" role="img" aria-label={`Score ${result.score} out of 100`}>
            <svg width="132" height="132" viewBox="0 0 132 132">
              <circle cx="66" cy="66" r={r} fill="none" stroke="var(--surface-2)" strokeWidth="12" />
              <circle cx="66" cy="66" r={r} fill="none" stroke={LEVEL_COLORS[idx]} strokeWidth="12"
                strokeLinecap="round" strokeDasharray={`${filled} ${circumference}`} />
            </svg>
            <div className="center">
              <div><div className="score">{Math.round(result.score)}</div><div className="of">/ 100</div></div>
            </div>
          </div>
          <div>
            <div className="card-sub" style={{ margin: 0 }}>Your current level</div>
            <div className="level-name">{result.level}</div>
            <div className="level-meta">Score {result.score} on the Junior → Lead scale</div>
            <div className="stat-row">
              <div className="stat">
                <div className="k">Market value (est.)</div>
                <div className="v">{formatMoney(result.salary_usd)}/yr</div>
                {result.salary_range && (
                  <div className="range" title="On unseen test data, 80% of real salaries fell inside this range">
                    likely {formatMoney(result.salary_range.low)} – {formatMoney(result.salary_range.high)}
                  </div>
                )}
              </div>
              <div className="stat">
                <div className="k">Model confidence</div>
                <div className="v">{Math.round((result.confidence ?? 0) * 100)}%</div>
                <div className="range">{result.known_skills_used.length} skills recognised</div>
              </div>
            </div>
          </div>
        </div>
        <div>
          <div className="card-sub" style={{ marginBottom: 10 }}>How sure is the model? (probability of each level)</div>
          <div className="prob-list">
            {levels.map((lvl, i) => (
              <div className="prob" key={lvl} title={`${lvl}: ${(result.probabilities[lvl] * 100).toFixed(1)}%`}>
                <span style={{ fontWeight: lvl === result.level ? 650 : 400 }}>{lvl}</span>
                <div className="track">
                  <div className="fill" style={{ width: `${result.probabilities[lvl] * 100}%`, background: LEVEL_COLORS[i] }} />
                </div>
                <span className="val">{(result.probabilities[lvl] * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
