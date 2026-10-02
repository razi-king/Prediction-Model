# DevAscend: Developer Growth Predictor

A developer enters their profile. DevAscend predicts their **current level** (Junior / Mid / Senior / Lead + 0–100 score), their **market value with a likely range**, a **3-year growth curve**, the **time to reach their goal**, a **skill gap analysis** and **what-if boosts**. It also gives a **learning guide**: what to learn next (e.g. HTML/CSS → Tailwind), workplace skills juniors usually learn too late (validation, Git workflow, testing…), market trends (AI, TypeScript…) and a month-by-month roadmap with **free courses and docs**. A **Model accuracy** page shows Accuracy, F1, MAE, RMSE, R² and predicted vs actual on real test data.

Trained on **153,645 real developers** from the Stack Overflow Developer Surveys 2021–2025 (360,519 raw responses, stored in **Apache Cassandra**).

```
Survey CSVs ──ingest.py──► Cassandra ──clean.py──► clean.parquet ──train.py──► models (.joblib)
                                                                                   │
            Next.js + React dashboard ◄──── FastAPI (main.py) ◄── predictor.py ◄───┘
                                                 │
                                                 └──► Cassandra (prediction history)
```

## Folder structure

```
E:\Prediction Model\
├── docker-compose.yml     Cassandra database (Docker)
├── ml/
│   ├── data/raw/          survey_2021.csv … survey_2025.csv   ← the downloaded survey files
│   ├── config.py          all settings (paths, Cassandra, constants)
│   ├── cassandra_db.py    Cassandra connection + table definitions
│   ├── ingest.py          STEP 1  CSV → Cassandra
│   ├── clean.py           STEP 2  Cassandra → cleaned data + level labels
│   ├── features.py        profile → numbers (shared by training AND the API)
│   ├── train.py           STEP 3  compare 3 algorithms per model, save the best
│   ├── evaluate.py        STEP 4  errors on the test set (MAE, RMSE, R², % error…)
│   ├── trends.py          STEP 5  rising/declining skills + AI adoption per year
│   ├── predictor.py       Model C growth simulator + what-if engine
│   ├── recommender.py     learning guide (hybrid recommender)
│   ├── knowledge/learning_topics.json   52 topics: prerequisites, why, free resources
│   ├── notebooks/eda.ipynb   charts for the report
│   └── models/            trained models, meta.json, reports/*.png, training_log.txt
├── api/                   FastAPI backend (main.py, schemas.py, db.py)
├── web/                   Next.js + React frontend with a Three.js 3D design
└── docs/                  viva notes for every part, plus likely viva questions
```

## Requirements

- **Python 3.11+** (tested on 3.13)
- **Node.js 18+** (tested on 22)
- **Docker Desktop** (runs Cassandra)

## How to run it (Windows PowerShell)

Everything is already installed, trained and working on this PC, so you only need **steps 4–6**. Steps 1–3 are for setting it up from scratch.

### 1. Python environment (one time)
```powershell
cd "E:\Prediction Model"
python -m venv .venv
.\.venv\Scripts\pip install -r ml\requirements.txt -r api\requirements.txt
```

### 2. Get the data (one time)
Download the survey CSVs from the official Stack Overflow GitHub repository and save them as
`ml\data\raw\survey_<year>.csv`:

```powershell
foreach ($y in 2021..2025) { curl.exe -L -o "ml\data\raw\survey_$y.csv" "https://media.githubusercontent.com/media/StackExchange/Survey/main/packages/archive/$y/results.csv" }
```
(The same files are on https://survey.stackoverflow.co: click "Data & files" for each year. Use the `survey_results_public.csv` file from the zip.)

### 3. Load Cassandra + train (one time, about 10 minutes)
```powershell
docker compose up -d                       # start Cassandra (wait ~1 minute the first time)
cd ml
..\.venv\Scripts\python ingest.py          # 360k rows → Cassandra   (~4 min)
..\.venv\Scripts\python clean.py           # Cassandra → clean data   (~30 s)
..\.venv\Scripts\python train.py           # train + compare + evaluate + trends (~6 min)
cd ..
```
If Cassandra is not available, `python clean.py --source csv` reads the CSV files directly.

### 4. Start Cassandra (every time)
```powershell
docker compose up -d
```

### 5. Start the backend (terminal 1)
```powershell
cd "E:\Prediction Model\api"
..\.venv\Scripts\python -m uvicorn main:app --reload --port 8000
```
API docs, where you can try every endpoint: http://localhost:8000/docs

### 6. Start the frontend (terminal 2)
```powershell
cd "E:\Prediction Model\web"
npm install        # first time only
npm run dev
```
Open http://localhost:3000 (Next.js picks 3001 if 3000 is busy). Fill in the profile and press **Predict my growth**.

## Results (test set: 30,729 developers never seen in training)

| Model A: Level | Accuracy | F1 (macro) | Within ±1 level |
|---|---|---|---|
| Logistic Regression | 62.2% | 0.603 | 97.9% |
| Random Forest | 63.3% | 0.623 | 97.9% |
| **XGBoost** ✅ | **65.2%** | **0.646** | **97.9%** |

| Model B: Market value | R² (log salary) | MAE | RMSE |
|---|---|---|---|
| Linear Regression | 0.584 | $31,089 | $56,327 |
| Random Forest | 0.633 | $28,401 | $52,959 |
| **XGBoost** ✅ | **0.649** | **$27,810** | **$52,049** |

| Error vs real salary (XGBoost) | Value |
|---|---|
| Median % error | 25.5% |
| Within ±20% of real salary | 40.6% |
| 80% prediction interval | 0.575× – 1.783× the prediction (80.0% coverage) |
| Baseline MAE / RMSE (always predict median) | $49,222 / $74,183 |

Charts are in `ml/models/reports/` and `ml/notebooks/figures/`. The full explanation is in [`docs/`](docs/README.md).

## Deploy it online (free)

Website on **Vercel**, API on **Render**, Cassandra on **DataStax Astra DB**. Step-by-step guide: [`docs/10-deployment.md`](docs/10-deployment.md).
