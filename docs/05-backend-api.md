# 5. Backend API (FastAPI)
Code: `api/main.py`, `api/schemas.py`, `api/db.py`
Run: `cd api` then `..\.venv\Scripts\python -m uvicorn main:app --reload --port 8000`
Interactive docs: **http://localhost:8000/docs**. You can demo every endpoint there in the viva.

## How it works
- **Startup (lifespan)**: the models are loaded **once** into memory, and the API connects to Cassandra. Loading them on every request would be far too slow.
- **Validation**: Pydantic models in `schemas.py` check every request. For example, years must be between 0 and 50 and the goal type must be "level" or "salary". Bad input gets an automatic **422** error with an explanation.
- **CORS**: lets the Next.js site, which runs on another port, call the API from the browser.
- **Cassandra down?** The API still works; only the history feature is switched off (`/health` shows `"cassandra": false`).

## Endpoints
| Method | Path | Returns |
|---|---|---|
| GET | /health | `{"status":"ok","models_loaded":true,"cassandra":true}` |
| GET | /options | roles, countries, skills (by popularity), education levels, used to fill the form |
| GET | /model-info | metrics of all 6 trained algorithms, confusion matrix, feature importance |
| GET | /evaluation | full test-set report: accuracy, F1, MAE, RMSE, R², % errors, baselines, confusion matrix, errors per salary band/country/level, 12 real examples (from `ml/models/evaluation.json`) |
| POST | /predict | current level, score, probabilities, salary |
| POST | /growth | growth curve (36 months), checkpoints, time to goal; **saves to Cassandra** |
| POST | /analysis | skill gaps, what-if boosts, roadmap (with resource links), **learning guide** |
| GET | /history?limit=20 | latest predictions from Cassandra |

### POST /predict
```json
{ "years_code": 4, "years_pro": 2, "role": "Full-stack", "country": "India",
  "ed_level": 4, "skills": ["JavaScript", "React", "Node.js"] }
```
Response:
```json
{ "level": "Junior", "score": 21.2,
  "probabilities": {"Junior": 0.96, "Mid": 0.04, "Senior": 0.0, "Lead": 0.0},
  "salary_usd": 8200,
  "salary_range": {"low": 4600, "high": 15900, "confidence": 0.8},
  "confidence": 0.96,
  "known_skills_used": ["JavaScript", "React", "Node.js"] }
```
- `salary_range` is the **80% prediction interval**. On unseen test data, 80% of real salaries were inside this range (see `docs/08`).
- `confidence` is the probability of the predicted level.

### POST /growth and POST /analysis
```json
{ "profile": { ...same as /predict... },
  "hours_per_week": 10,
  "goal": { "type": "level", "level": "Senior" },
  "plan": ["Docker", "Go"] }
```
- For a salary goal, use `"goal": {"type": "salary", "salary": 60000}`.
- `plan` is optional. If it's left out, the recommended roadmap is used.

`/growth` returns `curve` (month 0–36, two scenarios), `checkpoints` (Now, 6m, 1y, 2y, 3y) and `time_to_goal` (months + text).
`/analysis` returns `skill_gaps`, `what_if`, `roadmap` and `guide`:
- `guide.next_skills`: knowledge-base topics such as Tailwind, TypeScript and system design, each with reasons and free resources
- `guide.essentials`: workplace skills juniors learn late, such as validation, Git workflow and testing
- `guide.market`: rising skills and AI tool adoption by year (see `docs/09`)

`/options` also includes skill names that only exist in the knowledge base (e.g. "Tailwind CSS", "GraphQL"), so users can say they know them. The ML models ignore those names; only the learning guide uses them.

## Frontend call order
1. `/predict` and `/analysis` run **in parallel** (`Promise.all`).
2. `/growth` runs with `plan = roadmap skills`, so the chart matches the roadmap.
3. `/history` is refreshed.
