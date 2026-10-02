"use client";

import { formatMoney, LEVEL_COLORS } from "@/lib/api";

const LEVELS = ["Junior", "Mid", "Senior", "Lead"];

/** Latest predictions, read back from the Cassandra `predictions` table via GET /history. */
export default function HistoryTable({ history }) {
  if (!history) return null;
  return (
    <div className="card">
      <div className="card-title">Recent predictions</div>
      <div className="card-sub">Stored in Cassandra (table devascend.predictions, newest first)</div>
      {!history.cassandra ? (
        <p className="hint">Cassandra is not connected — start it with <code>docker compose up -d</code>.</p>
      ) : history.items.length === 0 ? (
        <p className="hint">No predictions yet.</p>
      ) : (
        <div className="table-wrap">
          <table className="history">
            <thead>
              <tr><th>When</th><th>Role</th><th>Country</th><th>Pro yrs</th><th>Level</th><th>Value</th><th>Goal</th><th>Months</th></tr>
            </thead>
            <tbody>
              {history.items.map((h) => (
                <tr key={h.created_at}>
                  <td>{new Date(h.created_at).toLocaleString()}</td>
                  <td>{h.role}</td>
                  <td>{h.country}</td>
                  <td>{h.years_pro}</td>
                  <td><span className="badge" style={{ background: LEVEL_COLORS[LEVELS.indexOf(h.level)] }}>{h.level}</span></td>
                  <td>{formatMoney(h.salary_usd)}</td>
                  <td>{h.goal}</td>
                  <td>{h.months_to_goal ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
