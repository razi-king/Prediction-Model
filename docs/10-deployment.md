# 10. Deployment (free)

DevAscend runs online on three free services:

| Part | Service | Address you get |
|---|---|---|
| Website (Next.js) | **Vercel** (Hobby, free) | `https://<project>.vercel.app` |
| API + ML models (FastAPI) | **Hugging Face Spaces** (Docker, free CPU) | `https://<user>-<space>.hf.space` |
| Cassandra (prediction history) | **DataStax Astra DB** (free tier) | managed Apache Cassandra |

```
Browser ──► Vercel (Next.js + Three.js) ──► Hugging Face Space (FastAPI + XGBoost) ──► Astra DB (Cassandra)
```

The models are already trained (`ml/models/`, in the GitHub repo), so the online API needs neither
the 650 MB survey files nor the local Cassandra. Training stays on the laptop: data in local Cassandra,
then `train.py`. The online Cassandra only stores the predictions people make on the website.

Code: <https://github.com/razi-king/Prediction-Model>

---

## What was changed in the code for deployment

| File | Change |
|---|---|
| `ml/config.py` | new settings `ASTRA_DB_TOKEN`, `ASTRA_DB_SECURE_BUNDLE`, `ASTRA_DB_SECURE_BUNDLE_B64`, `CASSANDRA_KEYSPACE` (from environment variables) |
| `ml/cassandra_db.py` | `make_cluster()` connects to **Astra** when `ASTRA_DB_TOKEN` is set, otherwise to local Docker; on Astra the keyspace is not created with CQL |
| `api/db.py` | uses `make_cluster()`, so the API works with local or cloud Cassandra |
| `api/main.py` | CORS reads `ALLOWED_ORIGINS` / `ALLOWED_ORIGIN_REGEX` so the Vercel site may call the API; new `/` landing route |
| `api/requirements.txt` | exact library versions the models were trained with (a saved model may not load in another scikit-learn/XGBoost version) |
| `Dockerfile`, `.dockerignore` | build the API as a container (also to test locally) |
| `deploy/huggingface/Dockerfile`, `deploy/huggingface/README.md` | the two files for the Hugging Face Space; the Space downloads the code from GitHub while building |
| `deploy/encode_astra_bundle.py` | turns the Astra connection zip into text for a Hugging Face secret |
| `web/lib/api.js`, `web/app/page.js`, `web/components/Header.jsx`, `web/app/accuracy/page.js` | wait and show "Waking up the server…" while a sleeping free API starts |
| `.gitignore` | never commit `*.zip`, `.env` or the encoded bundle (they are secrets) |

Nothing changes locally: without the `ASTRA_*` variables everything runs exactly as before.

---

## Step 0 — push the latest code to GitHub

```bash
cd "E:\Prediction Model"
git add .
git commit -m "Prepare deployment: Astra DB, Docker, CORS, wake-up handling"
git push
```

## Step 1 — Cassandra in the cloud: DataStax Astra DB

1. Go to **astra.datastax.com** and sign up (Google / GitHub login works).
2. **Create Database** → type **Serverless (Vector)** or **Serverless (Non-Vector)** if offered, any free cloud region close to you.
   - Database name: `devascend`
   - Keyspace name: `devascend` (if it asks; otherwise add it later under the database's **Data Explorer / Keyspaces**: *Add keyspace* → `devascend`).
3. Wait until the status is **Active**.
4. **Connect** tab → download the **Secure Connect Bundle** (a file like `secure-connect-devascend.zip`). Keep it private.
5. **Generate Token** (role: *Database Administrator*) → copy the token that starts with `AstraCS:`. It is shown only once.
6. Turn the zip into text for Hugging Face:
   ```bash
   cd "E:\Prediction Model"
   .venv\Scripts\python deploy\encode_astra_bundle.py "C:\Users\Admin\Downloads\secure-connect-devascend.zip"
   ```
   This writes `deploy\astra_bundle_b64.txt` (git ignores it).
7. (Optional) Test from your laptop before deploying:
   ```bash
   cd "E:\Prediction Model\api"
   $env:ASTRA_DB_TOKEN="AstraCS:..."; $env:ASTRA_DB_SECURE_BUNDLE="C:\Users\Admin\Downloads\secure-connect-devascend.zip"
   ..\.venv\Scripts\python -m uvicorn main:app --port 8000
   ```
   The log should say `Connected to Cassandra (Astra DB cloud)`. Close that terminal afterwards; new terminals go back to local Cassandra.

## Step 2 — the API: Hugging Face Spaces

1. Go to **huggingface.co** and sign up.
2. **New → Space**:
   - Space name: `devascend-api`
   - License: any (e.g. MIT)
   - SDK: **Docker** → *Blank*
   - Hardware: **CPU basic (free)**
   - Visibility: **Public**
3. In the new Space: **Files → Add file → Upload files** and upload the two files from
   `E:\Prediction Model\deploy\huggingface\`: **`Dockerfile`** and **`README.md`** (replace the existing README).
   Commit.
4. **Settings → Variables and secrets**, add:

   | Type | Name | Value |
   |---|---|---|
   | Secret | `ASTRA_DB_TOKEN` | the `AstraCS:...` token |
   | Secret | `ASTRA_DB_SECURE_BUNDLE_B64` | the whole content of `deploy\astra_bundle_b64.txt` |
   | Variable | `ALLOWED_ORIGINS` | your Vercel address, filled in after Step 3 (e.g. `https://devascend.vercel.app`) |

5. The Space builds automatically (**Logs** tab, a few minutes). When it shows **Running**, open
   `https://<your-hf-user>-devascend-api.hf.space/health` → `{"status":"ok","models_loaded":true,"cassandra":true}`
   and `/docs` for the interactive API.
   - The exact address is under the Space's **⋮ → Embed this Space → Direct URL**.
   - `cassandra:false` means the token or bundle secret is wrong; predictions still work.

## Step 3 — the website: Vercel

1. Go to **vercel.com** → sign up **with GitHub**.
2. **Add New → Project** → import `razi-king/Prediction-Model`.
3. Settings before deploying:
   - **Root Directory: `web`** (important; the Next.js app lives there)
   - Framework preset: Next.js (detected automatically)
   - **Environment Variable**: `NEXT_PUBLIC_API_URL` = your Space address from Step 2, e.g. `https://razi-king-devascend-api.hf.space` (no `/` at the end)
4. **Deploy**. You get an address such as `https://prediction-model-xyz.vercel.app`
   (rename it under *Settings → Domains*, e.g. `devascend.vercel.app`, if the name is free).

## Step 4 — connect them (CORS)

1. Back on Hugging Face → Space **Settings → Variables and secrets** → set `ALLOWED_ORIGINS` to your exact Vercel address,
   e.g. `https://devascend.vercel.app` (several: separate with commas; no `/` at the end).
2. The Space restarts. Open your Vercel site: the **API** and **Cassandra** dots should turn green and
   *Predict my growth* should work. The Recent predictions table now reads from Astra DB.

## Updating later

| You changed | Do this |
|---|---|
| Website code (`web/`) | `git push` → Vercel redeploys automatically |
| API or ML code / models | `git push`, then Space **Settings → Factory rebuild** (pulls the latest GitHub code) |
| Retrained models | commit the new `ml/models/*` files, push, Factory rebuild |

## Free-plan behaviour (say this in the viva)

- **Sleeping:** a free Space sleeps when nobody uses it. The first visit wakes it (can take a minute); the site shows
  "Waking up the server…" and continues by itself. Open the site a few minutes before a demo.
- **Astra free tier:** a managed Cassandra cluster with free monthly usage; plenty for prediction history.
- **3D design:** runs in the visitor's browser (WebGL), so hosting does not affect it.
- **Secrets** (Astra token, bundle) live only in Hugging Face's secret settings, never in GitHub.
- **Demo safety:** run the laptop version as the main demo; show the online link as a bonus.

## Troubleshooting

| Problem | Fix |
|---|---|
| Website says "Cannot reach the API" | `NEXT_PUBLIC_API_URL` wrong in Vercel (check spelling, no trailing `/`), then *Redeploy* |
| Browser console: "blocked by CORS policy" | `ALLOWED_ORIGINS` on the Space must exactly equal the Vercel address (https, no trailing `/`) |
| Space build fails at `pip install` | open **Logs**; usually a typo in an uploaded file; re-upload `deploy/huggingface/Dockerfile` |
| Space log: "Cassandra unavailable" | check the two Astra secrets; the token must start with `AstraCS:`; the database must be *Active* (a long-idle free Astra DB may hibernate: open it in the Astra console to resume) |
| Vercel build fails | Root Directory must be `web` |
