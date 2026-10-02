# 1. Project overview

## The problem
Developers often ask: *"Where am I in my career? How long until I'm Senior? What should I learn next?"*
DevAscend answers these questions using machine learning trained on real developer data.

## Inputs (from the user)
| Input | Example |
|---|---|
| Years of coding, years professional | 4, 2 |
| Main role | Full-stack |
| Skills (languages, frameworks, tools, databases, cloud) | JavaScript, React, Node.js, MongoDB |
| Education, country | Bachelor's, India |
| Study hours per week | 10 |
| Goal | Reach "Senior" **or** reach $60,000/year |

## Outputs
1. **Current level** (Junior/Mid/Senior/Lead) + **score 0–100** + estimated market value
2. **Growth curve** for the next 3 years (line chart, with and without learning)
3. **Time to goal**, e.g. "At 10 hrs/week you'll reach Senior in ~5 years"
4. **Skill gap analysis**: skills that higher-level developers in your role have and you don't
5. **What-if boosts**, e.g. "Learn Docker → +21% market value, goal 8 months sooner"
6. **Learning roadmap**: month-by-month skill-tree plan with free resources
7. **Learning guide**: what to learn next (e.g. HTML/CSS → Tailwind), "things juniors learn too late" (validation, Git workflow, testing…), and market trends such as AI tool use rising from 43% to 81%
8. **Model accuracy page**: Accuracy, F1, MAE, RMSE, R², % error, confusion matrix, and predicted vs actual for real test developers
9. **Salary range**: "likely $X – $Y" (80% prediction interval)

## The big idea (important for viva)
No public dataset follows the **same** developers over many years. So we:
1. **Learn** from 150k+ developers who are at **different** career stages (cross-sectional data).
2. **Simulate** one user moving forward in time: every month we add experience (and new skills
   based on study hours) and ask the trained models again.

## Pipeline
```
1. ingest.py   survey CSVs (5 years)  ──►  Cassandra table survey_responses   (360,519 rows)
2. clean.py    Cassandra  ──►  filtering, text→numbers, level labels  ──►  clean.parquet (153,645 rows)
3. train.py    clean data ──►  features ──►  3 algorithms × 2 models  ──►  best models (.joblib)
4. evaluate.py   errors on the test set (MAE, RMSE, R², confusion matrix…) → evaluation.json
   trends.py     rising/declining skills + AI adoption per year → trends.json
5. predictor.py  Model C (growth simulator) + what-if engine + learning guide (recommender.py)
6. api/main.py   FastAPI exposes /predict, /growth, /analysis, /evaluation, /history
7. web/          Next.js dashboard (Predictor page + Model accuracy page)
```

## Tech stack and why
| Part | Tool | Why |
|---|---|---|
| Storage | **Apache Cassandra** | Distributed NoSQL database built for large write-heavy data; fast queries by partition key |
| Data processing | pandas, numpy | Standard Python tools for tables |
| ML | scikit-learn, XGBoost | Easy-to-explain classic algorithms; XGBoost is state of the art for tabular data |
| Saving models | joblib | Saves trained Python objects to disk efficiently |
| Backend | FastAPI | Fast, automatic validation (Pydantic) and automatic docs at /docs |
| Frontend | Next.js + React + Recharts | Component-based UI, line charts with tooltips |
| Infrastructure | Docker Compose | One command starts Cassandra on any OS |
