"use client";

import Link from "next/link";
import { formatMoney } from "@/lib/api";

/** "How the model works" panel: the algorithm comparison from training (GET /model-info). */
export default function ModelInfo({ info }) {
  if (!info) return null;
  return (
    <div className="card">
      <details className="about">
        <summary>How the models were chosen (algorithm comparison)</summary>
        <div className="grid-2">
          <div className="table-wrap">
            <div className="card-sub">Model A — Level classifier · best: <b>{info.level_model}</b></div>
            <table className="boosts">
              <thead><tr><th>Algorithm</th><th>Accuracy</th><th>F1 (macro)</th><th>±1 level</th></tr></thead>
              <tbody>
                {info.level_results.map((r) => (
                  <tr key={r.model}>
                    <td className="skill">{r.model}</td>
                    <td>{(r.accuracy * 100).toFixed(1)}%</td>
                    <td>{r.f1_macro.toFixed(3)}</td>
                    <td>{(r.within_one_level * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="table-wrap">
            <div className="card-sub">Model B — Market value regressor · best: <b>{info.value_model}</b></div>
            <table className="boosts">
              <thead><tr><th>Algorithm</th><th>R² (log)</th><th>MAE</th><th>RMSE</th></tr></thead>
              <tbody>
                {info.value_results.map((r) => (
                  <tr key={r.model}>
                    <td className="skill">{r.model}</td>
                    <td>{r.r2_log.toFixed(3)}</td>
                    <td>{formatMoney(r.mae_usd)}</td>
                    <td>{formatMoney(r.rmse_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <p className="small-note">
          Trained on {info.train_rows.toLocaleString()} developers, tested on {info.test_rows.toLocaleString()} unseen
          developers (80/20 split) from the Stack Overflow Developer Surveys 2021–2025.{" "}
          <Link href="/accuracy">See the full accuracy report →</Link>
        </p>
      </details>
    </div>
  );
}
