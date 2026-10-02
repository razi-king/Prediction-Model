"use client";

import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatMoney } from "@/lib/api";

const METRICS = {
  score: { label: "Level score", plan: "score_with_plan", base: "score_experience_only", fmt: (v) => v.toFixed(0) },
  salary: { label: "Market value", plan: "salary_with_plan", base: "salary_experience_only", fmt: formatMoney },
};

const monthLabel = (m) => (m === 0 ? "Now" : m % 12 === 0 ? `${m / 12}y` : `${m}m`);

function ChartTooltip({ active, payload, label, metric }) {
  if (!active || !payload?.length) return null;
  const m = METRICS[metric];
  return (
    <div className="tooltip">
      <div className="t">{label === 0 ? "Now" : `Month ${label}`}</div>
      {payload.map((p) => (
        <div className="r" key={p.dataKey}>
          <span className="key-line" style={{ background: p.color }} />
          <b>{m.fmt(p.value)}</b>
          <span style={{ color: "var(--muted)" }}>{p.name}</span>
        </div>
      ))}
    </div>
  );
}

/** Output 2: growth curve over the next 36 months — two scenarios on ONE y-axis. */
export default function GrowthChart({ curve }) {
  const [metric, setMetric] = useState("score");
  const m = METRICS[metric];

  return (
    <div className="card">
      <div className="chart-head">
        <div>
          <div className="card-title">Growth curve — next 3 years</div>
          <div className="legend">
            <span><span className="key-line" style={{ background: "var(--accent)" }} />With learning roadmap</span>
            <span><span className="key-line" style={{ background: "var(--accent-2)" }} />Experience only</span>
          </div>
        </div>
        <div className="segmented" style={{ minWidth: 230 }}>
          {Object.entries(METRICS).map(([key, v]) => (
            <button key={key} type="button" className={metric === key ? "active" : ""} onClick={() => setMetric(key)}>{v.label}</button>
          ))}
        </div>
      </div>
      <div style={{ width: "100%", height: 300 }}>
        <ResponsiveContainer>
          <LineChart data={curve} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="month" ticks={[0, 6, 12, 18, 24, 30, 36]} tickFormatter={monthLabel}
              stroke="var(--axis)" tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} />
            <YAxis tickFormatter={(v) => (metric === "salary" ? `$${Math.round(v / 1000)}k` : v)}
              domain={metric === "score" ? [0, 100] : ["auto", "auto"]}
              stroke="var(--axis)" tick={{ fill: "var(--muted)", fontSize: 12 }} tickLine={false} axisLine={false} width={52} />
            <Tooltip content={<ChartTooltip metric={metric} />} cursor={{ stroke: "var(--axis)", strokeWidth: 1 }} />
            <Line type="monotone" dataKey={m.plan} name="With roadmap" stroke="var(--accent)" strokeWidth={2}
              dot={false} activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--surface)" }} />
            <Line type="monotone" dataKey={m.base} name="Experience only" stroke="var(--accent-2)" strokeWidth={2}
              strokeDasharray="5 4" dot={false} activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--surface)" }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="small-note">
        Simulation: every month adds 1/12 year of experience; the roadmap line also adds the next planned skill
        whenever enough study hours are completed. Both models are re-run for every month.
      </p>
    </div>
  );
}
