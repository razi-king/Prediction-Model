"use client";

/** Output 6: month-by-month learning roadmap built from the highest-impact skills. */
export default function Roadmap({ roadmap, hours }) {
  return (
    <div className="card">
      <div className="card-title">Your learning roadmap</div>
      <div className="card-sub">
        A skill-tree path: each step unlocks the next (e.g. React → Next.js). Timing uses each topic&apos;s study hours at {hours} h/week.
      </div>
      {roadmap.length === 0 ? (
        <p className="hint">Set study hours above 0 to get a roadmap.</p>
      ) : (
        <div className="timeline">
          {roadmap.map((step) => (
            <div className="step" key={step.name || step.skill}>
              <div className="when">
                {step.start_month === step.end_month ? `Month ${step.start_month}` : `Month ${step.start_month}–${step.end_month}`}
              </div>
              <div className="rail"><span className="node" /><span className="line" /></div>
              <div className="body">
                <div className="title">
                  {step.name || step.skill}
                  <span className="topic-meta" style={{ display: "inline-flex", marginLeft: 8 }}>
                    {step.category} · ~{step.hours} h{step.type === "essential" ? " · workplace essential" : ""}
                  </span>
                </div>
                <div className="why">{step.why}</div>
                <ul>{step.steps.map((s) => <li key={s}>{s}</li>)}</ul>
                {step.resources?.length > 0 && (
                  <div className="step-links">
                    {step.resources.map((r) => (
                      <a key={r.url} href={r.url} target="_blank" rel="noopener noreferrer">{r.title} ↗</a>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
