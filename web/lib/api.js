// All calls to the FastAPI backend live here, so components never hard-code URLs.
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request(path, body) {
  const res = await fetch(`${API_URL}${path}`, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {}
    throw new Error(`${path} failed: ${detail}`);
  }
  return res.json();
}

export const api = {
  health: () => request("/health"),
  options: () => request("/options"),
  modelInfo: () => request("/model-info"),
  evaluation: () => request("/evaluation"),
  history: () => request("/history?limit=10"),
  predict: (profile) => request("/predict", profile),
  analysis: (payload) => request("/analysis", payload),
  growth: (payload) => request("/growth", payload),
};

export const formatMoney = (v) =>
  v == null ? "—" : `$${Math.round(v).toLocaleString("en-US")}`;

export const LEVEL_COLORS = ["var(--lvl-0)", "var(--lvl-1)", "var(--lvl-2)", "var(--lvl-3)"];
