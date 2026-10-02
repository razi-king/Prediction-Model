"""
STEP 4 — Evaluate the saved models: how far are predictions from the REAL data?

    python evaluate.py          (train.py also runs this automatically at the end)

Uses the SAME 80/20 split as train.py (same random_state) so we only score on the 20% of
developers the models never saw.

Writes:
  models/evaluation.json        all numbers (shown on the website's "Model accuracy" page)
  models/reports/*.png          error charts for the report
  meta.json -> "salary_interval" used by the API to show a likely salary RANGE

Metrics
  Level classifier : accuracy, precision, recall, F1 per level, confusion matrix,
                     within-one-level accuracy, mean level error, baseline accuracy
  Market value     : R², MAE, RMSE, MAPE, median % error, % of predictions within ±10/20/30%,
                     bias (average over/under-prediction), errors per salary band and per country,
                     baseline errors, 80% prediction interval
"""
import json

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, mean_absolute_error,
                             mean_squared_error, precision_recall_fscore_support, r2_score)
from sklearn.model_selection import train_test_split

from config import CLEAN_FILE, LEVELS, MODELS_DIR, RANDOM_STATE, REPORTS_DIR
from features import build_features


def test_split(df, meta):
    X = build_features(df, meta)
    y_level = df["level"].map({lvl: i for i, lvl in enumerate(LEVELS)})
    _, idx_test = train_test_split(df.index, test_size=0.2, random_state=RANDOM_STATE, stratify=y_level)
    return X.loc[idx_test], y_level.loc[idx_test], df.loc[idx_test]


def evaluate_level(model, X, y):
    pred = model.predict(X)
    p, r, f, s = precision_recall_fscore_support(y, pred, labels=range(len(LEVELS)), zero_division=0)
    cm = confusion_matrix(y, pred, labels=range(len(LEVELS)))
    diff = np.abs(np.asarray(pred) - np.asarray(y))
    majority = int(pd.Series(y).mode()[0])
    return pred, {
        "accuracy": round(accuracy_score(y, pred), 4),
        "f1_macro": round(f1_score(y, pred, average="macro"), 4),
        "within_one_level": round(float((diff <= 1).mean()), 4),
        "off_by_two_or_more": round(float((diff >= 2).mean()), 4),
        "mean_level_error": round(float(diff.mean()), 3),          # 0 = perfect, 1 = one level off
        "baseline_accuracy": round(float((np.asarray(y) == majority).mean()), 4),  # always guess most common level
        "per_level": [
            {"level": LEVELS[i], "precision": round(float(p[i]), 3), "recall": round(float(r[i]), 3),
             "f1": round(float(f[i]), 3), "support": int(s[i])}
            for i in range(len(LEVELS))
        ],
        "confusion_matrix": cm.tolist(),
        # row-normalised: "of all real Seniors, what % were predicted as each level"
        "confusion_matrix_pct": (cm / cm.sum(axis=1, keepdims=True)).round(3).tolist(),
    }


def evaluate_value(model, X, y_true):
    y_true = np.asarray(y_true, dtype=float)
    pred = np.exp(model.predict(X))
    err = pred - y_true                       # + = model predicted too high
    pct = np.abs(err) / y_true                # relative error
    log_ratio = np.log(y_true / pred)         # used for the prediction interval

    q10, q90 = np.quantile(log_ratio, [0.10, 0.90])
    inside = ((y_true >= pred * np.exp(q10)) & (y_true <= pred * np.exp(q90))).mean()

    median_salary = np.median(y_true)         # baseline: always predict the median salary
    return pred, {
        "r2": round(r2_score(y_true, pred), 4),
        "r2_log": round(r2_score(np.log(y_true), np.log(pred)), 4),
        "mae": round(float(mean_absolute_error(y_true, pred)), 0),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, pred))), 0),
        "median_abs_error": round(float(np.median(np.abs(err))), 0),
        "mape_pct": round(float(pct.mean() * 100), 1),
        "median_pct_error": round(float(np.median(pct) * 100), 1),
        "within_10_pct": round(float((pct <= 0.10).mean()), 4),
        "within_20_pct": round(float((pct <= 0.20).mean()), 4),
        "within_30_pct": round(float((pct <= 0.30).mean()), 4),
        "bias_mean_error": round(float(err.mean()), 0),           # average over (+) / under (-) prediction
        "baseline_mae": round(float(np.mean(np.abs(y_true - median_salary))), 0),
        "baseline_rmse": round(float(np.sqrt(np.mean((y_true - median_salary) ** 2))), 0),
        "interval_80": {"low_factor": round(float(np.exp(q10)), 3), "high_factor": round(float(np.exp(q90)), 3),
                        "coverage": round(float(inside), 4)},
    }


def error_breakdowns(test_df, pred_salary):
    d = test_df.assign(pred=pred_salary)
    d["abs_err"] = (d["pred"] - d["salary_usd"]).abs()
    d["pct_err"] = d["abs_err"] / d["salary_usd"] * 100
    bands = [0, 25_000, 50_000, 100_000, 150_000, 1e9]
    labels = ["< $25k", "$25k–50k", "$50k–100k", "$100k–150k", "> $150k"]
    d["band"] = pd.cut(d["salary_usd"], bins=bands, labels=labels)
    by_band = d.groupby("band", observed=True).agg(
        developers=("pred", "size"), mae=("abs_err", "mean"), median_pct_error=("pct_err", "median"),
        avg_actual=("salary_usd", "mean"), avg_predicted=("pred", "mean")).round(0)
    top_countries = d["country"].value_counts().head(8).index
    by_country = d[d["country"].isin(top_countries)].groupby("country").agg(
        developers=("pred", "size"), mae=("abs_err", "mean"), median_pct_error=("pct_err", "median")).round(0)
    by_level = d.groupby("level").agg(mae=("abs_err", "mean"), median_pct_error=("pct_err", "median")).reindex(LEVELS).round(0)
    return (
        [{"band": k, **{c: float(v) for c, v in row.items()}} for k, row in by_band.iterrows()],
        [{"country": k, **{c: float(v) for c, v in row.items()}} for k, row in by_country.sort_values("developers", ascending=False).iterrows()],
        [{"level": k, **{c: float(v) for c, v in row.items()}} for k, row in by_level.iterrows()],
    )


def examples(test_df, pred_level, pred_salary, n=12):
    """A few real test developers: what they really are vs what the models predicted."""
    d = test_df.assign(pred_level=[LEVELS[i] for i in pred_level], pred_salary=pred_salary)
    sample = d.sample(n=n, random_state=7)
    rows = []
    for _, r in sample.iterrows():
        rows.append({
            "role": r["role"], "country": r["country"], "years_pro": float(r["years_pro"]),
            "num_skills": len(r["skills"].split(";")),
            "actual_level": r["level"], "predicted_level": r["pred_level"],
            "actual_salary": round(float(r["salary_usd"]), 0), "predicted_salary": round(float(r["pred_salary"]), -2),
            "error_pct": round(float((r["pred_salary"] - r["salary_usd"]) / r["salary_usd"] * 100), 1),
        })
    return rows


def save_charts(y_true, pred, level_eval):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    pct = (pred - y_true) / y_true * 100
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(np.clip(pct, -100, 200), bins=60, color="#2a78d6")
    ax.axvline(0, color="black", lw=1)
    ax.set_title("Market value: prediction error (%) on test developers")
    ax.set_xlabel("(predicted − actual) / actual  ×100   [clipped to −100..200]")
    ax.set_ylabel("developers")
    fig.tight_layout(); fig.savefig(REPORTS_DIR / "error_distribution.png", dpi=130); plt.close(fig)

    cm = np.array(level_eval["confusion_matrix_pct"]) * 100
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    im = ax.imshow(cm, cmap="Blues", vmin=0, vmax=100)
    ax.set_xticks(range(4), LEVELS); ax.set_yticks(range(4), LEVELS)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{cm[i, j]:.0f}%", ha="center", va="center", color="white" if cm[i, j] > 50 else "black")
    ax.set_xlabel("Predicted level"); ax.set_ylabel("Actual level")
    ax.set_title("Confusion matrix (% of each actual level)")
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout(); fig.savefig(REPORTS_DIR / "confusion_matrix_pct.png", dpi=130); plt.close(fig)


def run_evaluation():
    df = pd.read_parquet(CLEAN_FILE)
    with open(MODELS_DIR / "meta.json", encoding="utf-8") as f:
        meta = json.load(f)
    level_model = joblib.load(MODELS_DIR / "level_model.joblib")
    value_model = joblib.load(MODELS_DIR / "value_model.joblib")

    X_test, y_level, test_df = test_split(df, meta)
    pred_level, level_eval = evaluate_level(level_model, X_test, y_level)
    pred_salary, value_eval = evaluate_value(value_model, X_test, test_df["salary_usd"])
    by_band, by_country, by_level = error_breakdowns(test_df, pred_salary)

    evaluation = {
        "test_rows": int(len(test_df)),
        "level_model": meta["level_model"],
        "value_model": meta["value_model"],
        "level": level_eval,
        "value": {**value_eval, "by_salary_band": by_band, "by_country": by_country, "by_level": by_level},
        "examples": examples(test_df, pred_level, pred_salary),
        "algorithm_comparison": {"level": meta["level_results"], "value": meta["value_results"]},
    }
    with open(MODELS_DIR / "evaluation.json", "w", encoding="utf-8") as f:
        json.dump(evaluation, f, indent=1)
    meta["salary_interval"] = value_eval["interval_80"]
    with open(MODELS_DIR / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    save_charts(test_df["salary_usd"].to_numpy(), pred_salary, level_eval)

    L, V = level_eval, value_eval
    print(f"Evaluated on {len(test_df):,} unseen test developers")
    print(f"Level   : accuracy {L['accuracy']:.1%} (baseline {L['baseline_accuracy']:.1%}), "
          f"F1 {L['f1_macro']:.3f}, within +/-1 level {L['within_one_level']:.1%}, "
          f"off by 2+ levels {L['off_by_two_or_more']:.1%}")
    print(f"Salary  : R2 {V['r2']:.3f} (log {V['r2_log']:.3f}), MAE ${V['mae']:,.0f} (baseline ${V['baseline_mae']:,.0f}), "
          f"RMSE ${V['rmse']:,.0f} (baseline ${V['baseline_rmse']:,.0f})")
    print(f"          MAPE {V['mape_pct']}%, median error {V['median_pct_error']}%, "
          f"within +/-20%: {V['within_20_pct']:.1%}, bias ${V['bias_mean_error']:,.0f}")
    print(f"          80% interval: actual salary is between {V['interval_80']['low_factor']}x and "
          f"{V['interval_80']['high_factor']}x the prediction ({V['interval_80']['coverage']:.1%} of test devs)")
    print(f"Saved {MODELS_DIR / 'evaluation.json'}")


if __name__ == "__main__":
    run_evaluation()
