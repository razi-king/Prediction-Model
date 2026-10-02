"use client";

import { formatMoney } from "@/lib/api";

/** Output 3: time to goal (with plan vs experience only) + level/value checkpoints at 6m / 1y / 2y / 3y. */
export default function GoalCards({ growth, hours }) {
  const t = growth.time_to_goal;
  const saved =
    t.months_with_plan != null && t.months_experience_only != null
      ? t.months_experience_only - t.months_with_plan
      : null;

  return (
    <div className="card">
      <div className="card-sub" style={{ marginBottom: 6 }}>Time to goal · {t.goal}</div>
      <p className="goal-summary">{t.summary}</p>
      <div className="goal-compare">
        <div className="goal-box">
          <div className="k"><span className="key-line" style={{ background: "var(--accent)" }} />Following the roadmap ({hours} h/week)</div>
          <div className="v">{t.text_with_plan}</div>
        </div>
        <div className="goal-box">
          <div className="k"><span className="key-line" style={{ background: "var(--accent-2)" }} />Experience only (no new skills)</div>
          <div className="v">{t.text_experience_only}</div>
        </div>
      </div>
      {saved > 0 && <p className="goal-saving">▲ The roadmap gets you there {saved} months sooner</p>}

      <div className="card-sub" style={{ margin: "20px 0 10px" }}>Predicted level and market value (with roadmap)</div>
      <div className="checkpoints">
        {growth.checkpoints.map((c) => (
          <div className="checkpoint" key={c.month}>
            <div className="when">{c.label}</div>
            <div className="lvl">{c.level}</div>
            <div className="money">{formatMoney(c.salary_usd)}</div>
            <div className="money">score {Math.round(c.score)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
