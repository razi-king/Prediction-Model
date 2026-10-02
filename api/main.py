"""
DevAscend API (FastAPI).

Run from the api/ folder:
    uvicorn main:app --reload --port 8000
Interactive docs (try every endpoint in the browser): http://localhost:8000/docs

Endpoints
  GET  /health      is the API up, are the models loaded, is Cassandra connected
  GET  /options     lists for the form (roles, countries, skills, education levels)
  GET  /model-info  accuracy / R² of every algorithm we compared
  GET  /evaluation  detailed test-set errors: MAE, RMSE, R², % error, confusion matrix, examples
  POST /predict     current level, 0-100 score, market value
  POST /growth      growth curve (6m / 1y / 2y / 3y) + time to goal
  POST /analysis    skill gaps, what-if boosts, learning roadmap, learning guide
  GET  /history     latest predictions stored in Cassandra
"""
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# The ML code (features, predictor) lives in ../ml — make it importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ml"))

from db import PredictionStore                     # noqa: E402
from predictor import DevAscendPredictor          # noqa: E402
from schemas import PlanRequest, Profile          # noqa: E402

state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the models ONCE at startup (loading per request would be very slow).
    state["model"] = DevAscendPredictor()
    state["db"] = PredictionStore()
    state["db"].connect()
    yield
    state["db"].close()


app = FastAPI(title="DevAscend API", version="1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,   # lets the Next.js site (another port) call this API from the browser
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",   # any local port (3000, 3001...)
    allow_methods=["*"],
    allow_headers=["*"],
)


def model() -> DevAscendPredictor:
    return state["model"]


def check_profile(profile: Profile) -> dict:
    data = profile.model_dump()
    if data["role"] not in model().meta["roles"]:
        raise HTTPException(422, f"Unknown role '{data['role']}'. Use one of {model().meta['roles']}")
    if data["years_pro"] > data["years_code"]:
        data["years_code"] = data["years_pro"]
    return data


@app.get("/health")
def health():
    return {"status": "ok", "models_loaded": "model" in state, "cassandra": state["db"].available}


@app.get("/options")
def options():
    meta = model().meta
    skills = sorted(meta["skills"], key=lambda s: -meta["skill_popularity"].get(s, 0))
    # + skills from the knowledge base that the survey doesn't cover (Tailwind CSS, GraphQL...)
    extra = [s for s in model().guide.extra_skill_names() if s not in skills]
    return {
        "roles": meta["roles"],
        "countries": meta["countries"],
        "skills": skills + extra,
        "education_levels": [{"value": int(k), "label": v} for k, v in meta["education_levels"].items()],
        "levels": meta["levels"],
    }


@app.get("/model-info")
def model_info():
    meta = model().meta
    return {
        "level_model": meta["level_model"],
        "value_model": meta["value_model"],
        "level_results": meta["level_results"],
        "value_results": meta["value_results"],
        "confusion_matrix": meta["confusion_matrix"],
        "feature_importance_level": meta["feature_importance_level"],
        "feature_importance_value": meta["feature_importance_value"],
        "train_rows": meta["train_rows"],
        "test_rows": meta["test_rows"],
    }


@app.get("/evaluation")
def evaluation():
    """Written by ml/evaluate.py: how far the predictions are from the real test data."""
    path = Path(__file__).resolve().parent.parent / "ml" / "models" / "evaluation.json"
    if not path.exists():
        raise HTTPException(404, "Run `python evaluate.py` in the ml folder first")
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/predict")
def predict(profile: Profile):
    return model().predict(check_profile(profile))


@app.post("/growth")
def growth(req: PlanRequest):
    profile = check_profile(req.profile)
    goal = req.goal.model_dump()
    result = model().growth(profile, req.hours_per_week, goal, plan=req.plan or None)
    state["db"].save(profile, model().predict(profile), result)   # history in Cassandra
    return result


@app.post("/analysis")
def analysis(req: PlanRequest):
    profile = check_profile(req.profile)
    return model().analysis(profile, req.hours_per_week, req.goal.model_dump())


@app.get("/history")
def history(limit: int = Query(20, ge=1, le=100)):
    return {"cassandra": state["db"].available, "items": state["db"].latest(limit)}
