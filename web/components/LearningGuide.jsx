"use client";

import { useState } from "react";

const TYPE_LABEL = { docs: "Docs", course: "Course", video: "Video", book: "Book", practice: "Practice" };

function Resources({ items }) {
  return (
    <ul className="resources">
      {items.map((r) => (
        <li key={r.url}>
          <span className="res-type">{TYPE_LABEL[r.type] || r.type}</span>
          <a href={r.url} target="_blank" rel="noopener noreferrer">{r.title}</a>
        </li>
      ))}
    </ul>
  );
}

function TopicCard({ topic, rank }) {
  const [open, setOpen] = useState(rank < 2);
  return (
    <div className="topic">
      <button type="button" className="topic-head" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className="topic-rank">{rank + 1}</span>
        <span className="topic-title">
          <b>{topic.name}</b>
          <span className="topic-meta">
            {topic.category} · {topic.level} level · ~{topic.hours} h
            {topic.trend === "rising" && <span className="pill rising">▲ rising</span>}
            {topic.trend === "declining" && <span className="pill declining">▼ declining</span>}
          </span>
        </span>
        <span className="chev" aria-hidden>{open ? "−" : "+"}</span>
      </button>
      {open && (
        <div className="topic-body">
          <p>{topic.why}</p>
          {topic.reasons.length > 0 && (
            <ul className="reasons">{topic.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
          )}
          <div className="topic-cols">
            <div>
              <div className="mini-title">What to learn</div>
              <ul className="learn">{topic.learn.map((l) => <li key={l}>{l}</li>)}</ul>
            </div>
            <div>
              <div className="mini-title">Free resources</div>
              <Resources items={topic.resources} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/** Learning guide: next skills (knowledge base + ML + trends), hidden workplace essentials, market trends. */
export default function LearningGuide({ guide, level }) {
  if (!guide) return null;
  const ai = Object.entries(guide.market.ai_usage_by_year || {});

  return (
    <>
      <div className="card">
        <div className="card-title">Your learning guide: what to learn next</div>
        <div className="card-sub">
          Based on what you already know, your role and level ({level}), market trends from 5 years of survey data,
          and the ML model&apos;s market value boost.
        </div>
        <div className="topics">
          {guide.next_skills.map((t, i) => <TopicCard key={t.id} topic={t} rank={i} />)}
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">Things juniors usually learn too late</div>
          <div className="card-sub">Workplace skills that tutorials skip but every job expects</div>
          <div className="topics">
            {guide.essentials.length === 0
              ? <p className="hint">You already cover the essentials for your level.</p>
              : guide.essentials.map((t, i) => <TopicCard key={t.id} topic={t} rank={i} />)}
          </div>
        </div>

        <div className="card">
          <div className="card-title">Where the market is going</div>
          <div className="card-sub">Share of professional developers using each skill (Stack Overflow Survey)</div>
          {ai.length > 1 && (
            <div className="ai-trend">
              <div className="mini-title">Developers using AI tools</div>
              <div className="ai-bars">
                {ai.map(([year, v]) => (
                  <div key={year} className="ai-bar" title={`${year}: ${(v * 100).toFixed(0)}%`}>
                    <span className="ai-val">{(v * 100).toFixed(0)}%</span>
                    <div className="ai-fill" style={{ height: `${v * 80}%` }} />
                    <span className="ai-year">{year}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="mini-title" style={{ marginTop: 14 }}>Fastest-growing skills</div>
          <div className="bars">
            {guide.market.rising.map((r) => (
              <div className="bar-row" key={r.skill}
                title={`${r.skill}: ${(r.from * 100).toFixed(0)}% (${r.from_year}) → ${(r.to * 100).toFixed(0)}% (${r.to_year})`}>
                <span className="name">{r.skill}{r.you_have_it ? " ✓" : ""}</span>
                <div className="track">
                  <div className="fill" style={{ width: `${r.to * 100}%` }} />
                  <div className="mark" style={{ left: `calc(${r.from * 100}% - 1px)` }} />
                </div>
                <span className="val">{(r.from * 100).toFixed(0)}→{(r.to * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
          <div className="bar-legend">
            <span><span className="swatch" />Latest year</span>
            <span><span className="tick" />First year</span>
            <span>✓ = you have it</span>
          </div>
        </div>
      </div>
    </>
  );
}
