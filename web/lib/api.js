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

/**
 * A free hosted API (Hugging Face Space) goes to sleep when nobody uses it and needs some
 * time to wake up. Keep asking /health until it answers; onWaiting() lets the page show
 * "Waking up the server…" meanwhile. Locally it answers on the first try.
 */
export async function waitForApi(onWaiting, { tries = 30, delayMs = 5000 } = {}) {
  for (let i = 0; i < tries; i++) {
    try {
      return await request("/health");
    } catch {
      onWaiting?.(i + 1);
      await new Promise((r) => setTimeout(r, delayMs));
    }
  }
  throw new Error(`Cannot reach the API at ${API_URL}. Is the backend running?`);
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
