"use client";

import { Fragment, useEffect, useState } from "react";
import { api, formatMoney } from "@/lib/api";

const LEVELS = ["Junior", "Mid", "Senior", "Lead"];
const pct = (v, d = 1) => `${(v * 100).toFixed(d)}%`;

function Tile({ label, value, sub }) {
  return (
    <div className="tile">
      <div className="k">{label}</div>
      <div className="v">{value}</div>
      {sub && <div className="s">{sub}</div>}
    </div>
  );
}

/** Model vs a "dumb" baseline: shows how much better than guessing the model is. */
function CompareBars({ rows, format, lowerIsBetter }) {
  const max = Math.max(...rows.map((r) => r.value));
  return (
    <div className="compare">
      {rows.map((r) => (
        <div className="compare-row" key={r.label} title={`${r.label}: ${format(r.value)}`}>
          <span>{r.label}</span>
          <div className="track">
            <div className="fill" style={{ width: `${(r.value / max) * 100}%`, background: r.model ? "var(--accent)" : "var(--axis)" }} />
          </div>
          <span className="val">{format(r.value)}</span>
        </div>
      ))}
      <div className="small-note">{lowerIsBetter ? "Shorter bar = smaller error = better." : "Longer bar = better."}</div>
    </div>
  );
}

function ConfusionMatrix({ counts, percents }) {
  return (
    <>
      <div className="cm" role="table" aria-label="Confusion matrix">
        <div className="h">actual ↓ / predicted →</div>
        {LEVELS.map((l) => <div className="h" key={l}>{l}</div>)}
        {LEVELS.map((actual, i) => (
          <Fragment key={actual}>
            <div className="h">{actual}</div>
            {LEVELS.map((_, j) => {
              const p = percents[i][j];
              return (
                <div key={`${i}-${j}`} className="c" title={`Actual ${actual}, predicted ${LEVELS[j]}: ${counts[i][j].toLocaleString()} developers`}
                  style={{ background: `color-mix(in srgb, var(--accent) ${Math.round(p * 100)}%, var(--surface-2))`, color: p > 0.45 ? "var(--on-accent)" : "var(--ink)" }}>
                  {pct(p, 0)}<small>{counts[i][j].toLocaleString()}</small>
                </div>
              );
            })}
          </Fragment>
        ))}
      </div>
      <p className="cm-axis">Each row adds up to 100%. The diagonal = correct predictions. Most mistakes are one level away.</p>
    </>
  );
}

export default function AccuracyPage() {
  const [ev, setEv] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.evaluation().then(setEv).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="page"><div className="alert error">{error}</div></div>;
  if (!ev) return <div className="page"><div className="alert">Loading evaluation…</div></div>;

  const L = ev.level, V = ev.value;
  return (
    <div className="page">
      <div>
        <h1 className="page-title">How accurate is DevAscend?</h1>
        <p className="page-sub">
          All numbers below are measured on <b>{ev.test_rows.toLocaleString()} real developers the models never saw</b> during
          training (20% test set). We compare the models&apos; predictions with what these developers actually reported.
        </p>
      </div>

      {/* ---------------- Model A ---------------- */}
      <div className="card">
        <div className="card-title">Model A: Level classifier ({ev.level_model})</div>
        <div className="card-sub">Predicts Junior / Mid / Senior / Lead</div>
        <div className="tiles">
          <Tile label="Accuracy" value={pct(L.accuracy)} sub={`exactly the right level · guessing = ${pct(L.baseline_accuracy)}`} />
          <Tile label="F1 score (macro)" value={L.f1_macro.toFixed(3)} sub="balance of precision & recall, 1 = perfect" />
          <Tile label="Within ±1 level" value={pct(L.within_one_level)} sub="right level or a neighbour" />
          <Tile label="Mean level error" value={L.mean_level_error.toFixed(2)} sub={`levels off on average · ${pct(L.off_by_two_or_more)} off by 2+`} />
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">Confusion matrix</div>
          <div className="card-sub">Where the level predictions go right and wrong</div>
          <ConfusionMatrix counts={L.confusion_matrix} percents={L.confusion_matrix_pct} />
        </div>
        <div className="card">
          <div className="card-title">Per-level scores</div>
          <div className="card-sub">Precision = when we say “Senior”, how often it’s true · Recall = how many real Seniors we find</div>
          <div className="table-wrap">
            <table className="boosts">
              <thead><tr><th>Level</th><th>Precision</th><th>Recall</th><th>F1</th><th>Test devs</th></tr></thead>
              <tbody>
                {L.per_level.map((r) => (
                  <tr key={r.level}>
                    <td className="skill">{r.level}</td><td>{pct(r.precision)}</td><td>{pct(r.recall)}</td>
                    <td>{r.f1.toFixed(3)}</td><td>{r.support.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mini-title" style={{ marginTop: 16 }}>Model vs guessing the most common level</div>
          <CompareBars format={(v) => pct(v)} rows={[
            { label: `${ev.level_model} accuracy`, value: L.accuracy, model: true },
            { label: "Always guess one level", value: L.baseline_accuracy },
          ]} />
        </div>
      </div>

      {/* ---------------- Model B ---------------- */}
      <div className="card">
        <div className="card-title">Model B: Market value regressor ({ev.value_model})</div>
        <div className="card-sub">Predicts yearly salary in USD: how far from the real salary?</div>
        <div className="tiles">
          <Tile label="R² (log salary)" value={V.r2_log.toFixed(3)} sub={`share of salary differences explained · R² in $ = ${V.r2.toFixed(3)}`} />
          <Tile label="MAE (mean absolute error)" value={formatMoney(V.mae)} sub={`typical miss · median miss ${formatMoney(V.median_abs_error)}`} />
          <Tile label="RMSE (root mean squared error)" value={formatMoney(V.rmse)} sub="punishes big misses more than MAE" />
          <Tile label="Median % error" value={`${V.median_pct_error}%`} sub={`MAPE (mean % error) ${V.mape_pct}%`} />
          <Tile label="Within ±10%" value={pct(V.within_10_pct)} sub="of the real salary" />
          <Tile label="Within ±20%" value={pct(V.within_20_pct)} sub="of the real salary" />
          <Tile label="Within ±30%" value={pct(V.within_30_pct)} sub="of the real salary" />
          <Tile label="Bias" value={`${V.bias_mean_error >= 0 ? "+" : "−"}${formatMoney(Math.abs(V.bias_mean_error))}`}
            sub={V.bias_mean_error >= 0 ? "slightly over-predicts on average" : "slightly under-predicts on average"} />
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">Model vs baseline</div>
          <div className="card-sub">Baseline = always predict the median salary (no ML at all)</div>
          <div className="mini-title">MAE</div>
          <CompareBars lowerIsBetter format={formatMoney} rows={[
            { label: ev.value_model, value: V.mae, model: true },
            { label: "Median baseline", value: V.baseline_mae },
          ]} />
          <div className="mini-title" style={{ marginTop: 12 }}>RMSE</div>
          <CompareBars lowerIsBetter format={formatMoney} rows={[
            { label: ev.value_model, value: V.rmse, model: true },
            { label: "Median baseline", value: V.baseline_rmse },
          ]} />
          <p className="small-note">
            <b>Uncertainty range:</b> on test data, 80% of real salaries were between{" "}
            <b>{V.interval_80.low_factor}×</b> and <b>{V.interval_80.high_factor}×</b> the prediction
            (actual coverage {pct(V.interval_80.coverage)}). The predictor shows this as “likely $X – $Y”.
          </p>
        </div>
        <div className="card">
          <div className="card-title">Error by salary band</div>
          <div className="card-sub">The model is most accurate for typical salaries; extremes are harder</div>
          <div className="table-wrap">
            <table className="boosts">
              <thead><tr><th>Real salary</th><th>Devs</th><th>Avg real</th><th>Avg predicted</th><th>MAE</th><th>Median % err</th></tr></thead>
              <tbody>
                {V.by_salary_band.map((b) => (
                  <tr key={b.band}>
                    <td className="skill">{b.band}</td><td>{b.developers.toLocaleString()}</td>
                    <td>{formatMoney(b.avg_actual)}</td><td>{formatMoney(b.avg_predicted)}</td>
                    <td>{formatMoney(b.mae)}</td><td>{b.median_pct_error}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="small-note">
            Low salaries get over-predicted and very high salaries under-predicted. This is called “regression to the mean”:
            the survey can&apos;t see company, city or negotiation, so extreme salaries look more average to the model.
          </p>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">Error by country</div>
          <div className="card-sub">Top 8 countries in the test set</div>
          <div className="table-wrap">
            <table className="boosts">
              <thead><tr><th>Country</th><th>Devs</th><th>MAE</th><th>Median % err</th></tr></thead>
              <tbody>
                {V.by_country.map((c) => (
                  <tr key={c.country}>
                    <td className="skill">{c.country.replace("United Kingdom of Great Britain and Northern Ireland", "United Kingdom")}</td>
                    <td>{c.developers.toLocaleString()}</td><td>{formatMoney(c.mae)}</td><td>{c.median_pct_error}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="card">
          <div className="card-title">Error by level</div>
          <div className="card-sub">Salary error for each real level</div>
          <div className="table-wrap">
            <table className="boosts">
              <thead><tr><th>Level</th><th>MAE</th><th>Median % err</th></tr></thead>
              <tbody>
                {V.by_level.map((l) => (
                  <tr key={l.level}><td className="skill">{l.level}</td><td>{formatMoney(l.mae)}</td><td>{l.median_pct_error}%</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Real examples: predicted vs actual</div>
        <div className="card-sub">12 random developers from the test set</div>
        <div className="table-wrap">
          <table className="boosts">
            <thead>
              <tr><th>Role</th><th>Country</th><th>Pro yrs</th><th>Skills</th><th>Actual level</th><th>Predicted</th><th>Actual salary</th><th>Predicted</th><th>Error</th></tr>
            </thead>
            <tbody>
              {ev.examples.map((e, i) => (
                <tr key={i}>
                  <td>{e.role}</td>
                  <td>{e.country.replace("United Kingdom of Great Britain and Northern Ireland", "United Kingdom").replace("United States of America", "USA")}</td>
                  <td>{e.years_pro}</td><td>{e.num_skills}</td>
                  <td>{e.actual_level}</td>
                  <td className={e.actual_level === e.predicted_level ? "up" : ""}>{e.predicted_level}{e.actual_level === e.predicted_level ? " ✓" : ""}</td>
                  <td>{formatMoney(e.actual_salary)}</td><td>{formatMoney(e.predicted_salary)}</td>
                  <td className={Math.abs(e.error_pct) <= 20 ? "up" : "neg"}>{e.error_pct > 0 ? "+" : ""}{e.error_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Algorithm comparison (same 80/20 split)</div>
        <div className="grid-2" style={{ marginTop: 10 }}>
          <div className="table-wrap">
            <table className="boosts">
              <thead><tr><th>Level model</th><th>Accuracy</th><th>F1</th><th>±1 level</th></tr></thead>
              <tbody>
                {ev.algorithm_comparison.level.map((r) => (
                  <tr key={r.model}><td className="skill">{r.model}</td><td>{pct(r.accuracy)}</td><td>{r.f1_macro.toFixed(3)}</td><td>{pct(r.within_one_level)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="table-wrap">
            <table className="boosts">
              <thead><tr><th>Value model</th><th>R² (log)</th><th>MAE</th><th>RMSE</th></tr></thead>
              <tbody>
                {ev.algorithm_comparison.value.map((r) => (
                  <tr key={r.model}><td className="skill">{r.model}</td><td>{r.r2_log.toFixed(3)}</td><td>{formatMoney(r.mae_usd)}</td><td>{formatMoney(r.rmse_usd)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
