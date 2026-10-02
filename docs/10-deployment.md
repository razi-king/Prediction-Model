# 10. Deployment (free)

DevAscend runs online on three free services:

| Part | Service | Address you get |
|---|---|---|
| Website (Next.js) | **Vercel** (Hobby, free) | `https://<project>.vercel.app` |
| API + ML models (FastAPI) | **Render** (free web service, Docker) | `https://<service>.onrender.com` |
| Cassandra (prediction history) | **DataStax Astra DB** (free tier) | managed Apache Cassandra |

```
Browser ──► Vercel (Next.js + Three.js) ──► Render (FastAPI + XGBoost, Docker) ──► Astra DB (Cassandra)
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
| `Dockerfile`, `.dockerignore` | build the API as a container: Render builds this file from GitHub (also to test locally) |
| `deploy/huggingface/` | alternative host (Hugging Face Docker Spaces now need a paid plan, so Render is used) |
| `deploy/download_astra_bundle.py` | downloads the Astra connection zip with Astra's API (when the portal button is disabled) |
| `deploy/encode_astra_bundle.py` | turns the Astra connection zip into text for a hosting secret |
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
6. Turn the zip into text for the hosting secret:
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

## Step 2 — the API: Render (free)

Hugging Face Docker Spaces now require a paid plan, so the API runs on **Render**'s free web service.
The API uses about **220 MB** of memory (measured), well inside the free 512 MB.

1. Go to **render.com** → **Get Started** → sign up **with GitHub**.
2. **+ New → Web Service** → connect GitHub if asked → pick **`razi-king/Prediction-Model`** → **Connect**.
3. Settings on the form:
   - **Name:** `devascend-api` (becomes `https://devascend-api.onrender.com`, or with a suffix if taken)
   - **Language / Runtime:** **Docker** (Render finds the `Dockerfile` in the repo root)
   - **Branch:** `main`, **Root Directory:** leave empty
   - **Instance Type:** **Free**
4. **Environment Variables** (on the same form, or later under *Environment*) → *Add Environment Variable*:

   | Key | Value |
   |---|---|
   | `ASTRA_DB_TOKEN` | the `AstraCS:...` token |
   | `ASTRA_DB_SECURE_BUNDLE_B64` | the whole content of `deploy\astra_bundle_b64.txt` |
   | `CASSANDRA_KEYSPACE` | `default_keyspace` (the keyspace shown in Astra's Data Explorer) |
   | `ALLOWED_ORIGINS` | your Vercel address, filled in after Step 3 |

5. *Advanced* → **Health Check Path:** `/health`.
6. **Create Web Service**. The first build takes about 5–10 minutes (Logs tab). Done when the log shows
   `Application startup complete` and the status is **Live**.
7. Open `https://<your-service>.onrender.com/health` → `{"status":"ok","models_loaded":true,"cassandra":true}`
   and `/docs` for the interactive API.

Render sets the `PORT` variable itself; the Dockerfile already listens on `$PORT`.

## Step 3 — the website: Vercel

1. Go to **vercel.com** → sign up **with GitHub**.
2. **Add New → Project** → import `razi-king/Prediction-Model`.
3. Settings before deploying:
   - **Root Directory: `web`** (important; the Next.js app lives there)
   - Framework preset: Next.js (detected automatically)
   - **Environment Variable**: `NEXT_PUBLIC_API_URL` = your Render address from Step 2, e.g. `https://devascend-api.onrender.com` (no `/` at the end)
4. **Deploy**. You get an address such as `https://prediction-model-xyz.vercel.app`
   (rename it under *Settings → Domains*, e.g. `devascend.vercel.app`, if the name is free).

## Step 4 — connect them (CORS)

1. Back on Render → your service → **Environment** → set `ALLOWED_ORIGINS` to your exact Vercel address,
   e.g. `https://devascend.vercel.app` (several: separate with commas; no `/` at the end).
2. Render redeploys by itself (about a minute). Open your Vercel site: the **API** and **Cassandra** dots should turn green and
   *Predict my growth* should work. The Recent predictions table now reads from Astra DB.

## Updating later

| You changed | Do this |
|---|---|
| Website code (`web/`) | `git push` → Vercel redeploys automatically |
| API or ML code / models | `git push` → Render redeploys automatically |
| Retrained models | commit the new `ml/models/*` files and push |

## Free-plan behaviour (say this in the viva)

- **Sleeping:** a free Render service sleeps after about 15 minutes without visitors. The first visit wakes it (can take a minute); the site shows
  "Waking up the server…" and continues by itself. Open the site a few minutes before a demo.
- **Astra free tier:** a managed Cassandra cluster with free monthly usage; plenty for prediction history.
- **3D design:** runs in the visitor's browser (WebGL), so hosting does not affect it.
- **Secrets** (Astra token, bundle) live only in Render's environment settings, never in GitHub.
- **Demo safety:** run the laptop version as the main demo; show the online link as a bonus.

## Troubleshooting

| Problem | Fix |
|---|---|
| Website says "Cannot reach the API" | `NEXT_PUBLIC_API_URL` wrong in Vercel (check spelling, no trailing `/`), then *Redeploy* |
| Browser console: "blocked by CORS policy" | `ALLOWED_ORIGINS` on Render must exactly equal the Vercel address (https, no trailing `/`) |
| Render build fails | open **Logs** and send the last lines; check Runtime is **Docker** and Root Directory is empty |
| Render log: "Cassandra unavailable" | check the two Astra secrets; the token must start with `AstraCS:`; the database must be *Active* (a long-idle free Astra DB may hibernate: open it in the Astra console to resume) |
| Vercel build fails | Root Directory must be `web` |
