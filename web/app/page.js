"use client";

import { useEffect, useState } from "react";
import GoalCards from "@/components/GoalCards";
import GrowthChart from "@/components/GrowthChart";
import HistoryTable from "@/components/HistoryTable";
import LevelBadge from "@/components/LevelBadge";
import ModelInfo from "@/components/ModelInfo";
import ProfileForm from "@/components/ProfileForm";
import Roadmap from "@/components/Roadmap";
import SkillGapBars from "@/components/SkillGapBars";
import WhatIfList from "@/components/WhatIfList";
import LearningGuide from "@/components/LearningGuide";
import Hero from "@/components/Hero";
import { api, API_URL } from "@/lib/api";

// Example profile so the form is never empty
const DEFAULT_FORM = {
  years_code: 2,
  years_pro: 1,
  role: "Front-end",
  country: "India",
  ed_level: 4,
  skills: ["HTML/CSS", "JavaScript", "React"],
  hours_per_week: 10,
  goal_type: "level",
  goal_level: "Senior",
  goal_salary: 60000,
};

export default function Home() {
  const [options, setOptions] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [history, setHistory] = useState(null);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null); // { prediction, analysis, growth, hours }

  // On page load: get dropdown options, API status, model metrics and history.
  useEffect(() => {
    api.options().then(setOptions).catch(() => setError(`Cannot reach the API at ${API_URL}. Is the backend running?`));
    api.modelInfo().then(setModelInfo).catch(() => {});
    api.history().then(setHistory).catch(() => {});
  }, []);

  async function runPrediction() {
    setLoading(true);
    setError("");
    const profile = {
      years_code: form.years_code,
      years_pro: form.years_pro,
      role: form.role,
      country: form.country,
      ed_level: form.ed_level,
      skills: form.skills,
    };
    const payload = {
      profile,
      hours_per_week: form.hours_per_week,
      goal: form.goal_type === "level"
        ? { type: "level", level: form.goal_level }
        : { type: "salary", salary: form.goal_salary },
    };
    try {
      // 1) current level + 2) skill analysis can run at the same time
      const [prediction, analysis] = await Promise.all([api.predict(profile), api.analysis(payload)]);
      // 3) growth uses the roadmap skills from the analysis as the learning plan
      const growth = await api.growth({ ...payload, plan: analysis.roadmap.map((s) => s.skill) });
      setResult({ prediction, analysis, growth, hours: form.hours_per_week, role: form.role });
      api.history().then(setHistory).catch(() => {});
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>

      <Hero />
      <div className="layout">
        <aside className="sidebar card" id="profile">
          {options ? (
            <ProfileForm
              options={options} form={form} setForm={setForm} onSubmit={runPrediction}
              loading={loading} error={error} errors={errors} setErrors={setErrors}
            />
          ) : (
            <div className={error ? "alert error" : "alert"}>{error || "Loading form…"}</div>
          )}
        </aside>

        <main className="main">
          {!result ? (
            <div className="card empty">
              <div>
                <h2>See where your career is heading</h2>
                <p>Fill in your profile and press <b>Predict my growth</b>.</p>
                <p className="small-note">You&apos;ll get your level, a 3-year growth curve, time to your goal, skill gaps and a learning roadmap.</p>
              </div>
            </div>
          ) : (
            <>
              <LevelBadge result={result.prediction} levels={options.levels} />
              <GoalCards growth={result.growth} hours={result.hours} />
              <GrowthChart curve={result.growth.curve} />
              <div className="grid-2">
                <SkillGapBars gaps={result.analysis.skill_gaps} level={result.prediction.level} role={result.role} />
                <WhatIfList boosts={result.analysis.what_if} />
              </div>
              <Roadmap roadmap={result.analysis.roadmap} hours={result.hours} />
              <LearningGuide guide={result.analysis.guide} level={result.prediction.level} />
            </>
          )}
          <ModelInfo info={modelInfo} />
          <HistoryTable history={history} />
        </main>
      </div>
    </>
  );
}
