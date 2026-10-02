"use client";

import Link from "next/link";

/** Big title area at the top of the home page; the 3D crystal floats beside it. */
export default function Hero() {
  return (
    <section className="hero">
      <p className="hero-eyebrow">Developer growth predictor · machine learning</p>
      <h1 className="hero-title">DevAscend</h1>
      <p className="hero-sub">
        Find out where you stand, how fast you will grow and exactly what to learn next. Predictions come from
        models trained on 153,645 real developers.
      </p>
      <div className="hero-stats">
        <span className="hero-stat"><b>153,645</b> developers</span>
        <span className="hero-stat"><b>5 years</b> of survey data in Cassandra</span>
        <span className="hero-stat"><b>97.9%</b> within one level</span>
        <span className="hero-stat"><b>52</b> learning topics</span>
      </div>
      <div className="hero-actions">
        <a href="#profile" className="btn">Predict my growth ↓</a>
        <Link href="/accuracy" className="btn ghost">See model accuracy</Link>
      </div>
    </section>
  );
}
