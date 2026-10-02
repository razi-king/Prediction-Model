"use client";

/** Output 4: skills that higher-level developers in your role use and you don't (yet). */
export default function SkillGapBars({ gaps, level, role }) {
  return (
    <div className="card">
      <div className="card-title">Skill gap analysis</div>
      <div className="card-sub">Share of higher-level {role} developers who use each skill you don't have yet</div>
      {gaps.length === 0 ? (
        <p className="hint">No big gaps found — you already use the common skills of your role.</p>
      ) : (
        <div className="bars">
          {gaps.map((g) => (
            <div className="bar-row" key={g.skill}
              title={`${g.skill}: ${(g.target_share * 100).toFixed(0)}% of higher-level devs vs ${(g.your_level_share * 100).toFixed(0)}% at ${level}`}>
              <span className="name">{g.skill}</span>
              <div className="track">
                <div className="fill" style={{ width: `${g.target_share * 100}%` }} />
                <div className="mark" style={{ left: `calc(${g.your_level_share * 100}% - 1px)` }} />
              </div>
              <span className="val">{(g.target_share * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      )}
      <div className="bar-legend">
        <span><span className="swatch" />Higher-level developers</span>
        <span><span className="tick" />Developers at your level ({level})</span>
      </div>
    </div>
  );
}
