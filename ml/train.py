"""
STEP 3 — Train and compare models, then save the best ones.

    python train.py            # full training (a few minutes)
    python train.py --fast     # smaller/faster settings for a quick test

Model A  Level Classifier   (Junior/Mid/Senior/Lead)   -> LogisticRegression vs RandomForest vs XGBoost
Model B  Market Value       (yearly salary in USD)      -> LinearRegression  vs RandomForest vs XGBoost

The SAME 80/20 train/test split is used for every algorithm so the comparison is fair.
The algorithm with the best test score is saved with joblib.

Outputs (ml/models/):
  level_model.joblib, value_model.joblib   the two winning models
  meta.json                                vocabulary, metrics, skill statistics used by the API
  reports/*.png                            charts for the project report
"""
import argparse
import json
import time

import joblib
import matplotlib

matplotlib.use("Agg")   # draw charts to files, no window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix, f1_score,
                             mean_absolute_error, mean_squared_error, r2_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier, XGBRegressor

from config import (CLEAN_FILE, LEVELS, MODELS_DIR, RANDOM_STATE, REPORTS_DIR, TOP_COUNTRIES,
                    TOP_SKILLS)
from features import EDUCATION_LEVELS, ROLES, build_features


# ---------------- 1. Vocabulary ----------------
def build_meta(df: pd.DataFrame) -> dict:
    """Decide which countries / skills become columns. Saved so the API uses the same list."""
    countries = df["country"].value_counts().head(TOP_COUNTRIES).index.tolist()
    skills = df["skills"].str.split(";").explode().value_counts().head(TOP_SKILLS).index.tolist()
    meta = {"roles": ROLES, "countries": countries + ["Other"], "skills": skills, "levels": LEVELS}
    meta["feature_columns"] = build_features(df.head(5), meta).columns.tolist()
    return meta


# ---------------- 2. Candidate algorithms ----------------
def monotone_constraints(columns):
    """+1 = prediction may only go UP when this feature goes up (more experience never hurts)."""
    return "(" + ",".join("1" if c in ("years_code", "years_pro") else "0" for c in columns) + ")"


def classifiers(columns, fast):
    n = 60 if fast else 150
    return {
        "Logistic Regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, C=0.5)),
        "Random Forest": RandomForestClassifier(
            n_estimators=n, max_depth=18, min_samples_leaf=5, max_samples=0.6,
            n_jobs=-1, random_state=RANDOM_STATE),
        "XGBoost": XGBClassifier(
            n_estimators=200 if fast else 500, max_depth=6, learning_rate=0.08,
            subsample=0.8, colsample_bytree=0.8, tree_method="hist", n_jobs=-1,
            random_state=RANDOM_STATE),
    }


def regressors(columns, fast):
    n = 60 if fast else 150
    return {
        "Linear Regression": make_pipeline(StandardScaler(), LinearRegression()),
        "Random Forest": RandomForestRegressor(
            n_estimators=n, max_depth=18, min_samples_leaf=5, max_samples=0.6,
            n_jobs=-1, random_state=RANDOM_STATE),
        "XGBoost": XGBRegressor(
            n_estimators=300 if fast else 800, max_depth=7, learning_rate=0.06,
            subsample=0.8, colsample_bytree=0.8, tree_method="hist", n_jobs=-1,
            monotone_constraints=monotone_constraints(columns), random_state=RANDOM_STATE),
    }


# ---------------- 3. Training + evaluation ----------------
def train_level_models(X_train, X_test, y_train, y_test, fast):
    print("\n=== Model A: Level Classifier ===")
    results, fitted = [], {}
    for name, model in classifiers(X_train.columns, fast).items():
        start = time.time()
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        row = {
            "model": name,
            "accuracy": round(accuracy_score(y_test, pred), 4),
            "f1_macro": round(f1_score(y_test, pred, average="macro"), 4),
            # "almost right": predicted level is the true level or one step away
            "within_one_level": round(float(np.mean(np.abs(np.asarray(pred) - np.asarray(y_test)) <= 1)), 4),
            "train_seconds": round(time.time() - start, 1),
        }
        results.append(row)
        fitted[name] = model
        print(f"  {name:<20} accuracy={row['accuracy']:.3f}  F1={row['f1_macro']:.3f}  "
              f"within-one-level={row['within_one_level']:.3f}  ({row['train_seconds']}s)")
    best = max(results, key=lambda r: r["f1_macro"])["model"]
    print(f"  -> best: {best}")
    return fitted, results, best


def train_value_models(X_train, X_test, y_train, y_test, fast):
    """Salary is very skewed, so the models learn log(salary) and we convert back with exp()."""
    print("\n=== Model B: Market Value Regressor ===")
    results, fitted = [], {}
    for name, model in regressors(X_train.columns, fast).items():
        start = time.time()
        model.fit(X_train, np.log(y_train))
        pred = np.exp(model.predict(X_test))
        row = {
            "model": name,
            "r2_log": round(r2_score(np.log(y_test), np.log(pred)), 4),
            "r2": round(r2_score(y_test, pred), 4),
            "mae_usd": round(mean_absolute_error(y_test, pred), 0),
            "rmse_usd": round(float(np.sqrt(mean_squared_error(y_test, pred))), 0),
            "train_seconds": round(time.time() - start, 1),
        }
        results.append(row)
        fitted[name] = model
        print(f"  {name:<20} R2(log)={row['r2_log']:.3f}  R2={row['r2']:.3f}  "
              f"MAE=${row['mae_usd']:,.0f}  RMSE=${row['rmse_usd']:,.0f}  ({row['train_seconds']}s)")
    best = max(results, key=lambda r: r["r2_log"])["model"]
    print(f"  -> best: {best}")
    return fitted, results, best


def feature_importance(model, columns, top=20):
    """Tree models: built-in importance. Linear models: size of the (scaled) coefficients."""
    est = model[-1] if hasattr(model, "steps") else model
    if hasattr(est, "feature_importances_"):
        values = est.feature_importances_
    else:
        values = np.abs(est.coef_).mean(axis=0) if est.coef_.ndim > 1 else np.abs(est.coef_)
    s = pd.Series(values, index=columns).sort_values(ascending=False).head(top)
    return {k: round(float(v), 5) for k, v in s.items()}


# ---------------- 4. Statistics used by the skill-gap analysis ----------------
def skill_stats_by_role(df: pd.DataFrame, skills: list) -> dict:
    """For each role and level: what share of developers use each skill (0..1)."""
    dummies = df["skills"].str.get_dummies(sep=";").reindex(columns=skills, fill_value=0)
    stats = {}
    for role in ROLES:
        mask = df["role"] == role
        if mask.sum() < 50:
            mask = pd.Series(True, index=df.index)   # tiny role -> use everyone
        by_level = dummies[mask].groupby(df.loc[mask, "level"]).mean()
        stats[role] = {lvl: by_level.loc[lvl].round(3).to_dict() for lvl in LEVELS if lvl in by_level.index}
    return stats


# ---------------- 5. Charts for the report ----------------
def save_charts(level_results, value_results, cm, imp_level, imp_value, y_test_value, pred_value):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    pd.DataFrame(level_results).set_index("model")[["accuracy", "f1_macro"]].plot.bar(ax=axes[0], rot=0)
    axes[0].set_title("Model A — Level Classifier"); axes[0].set_ylim(0, 1)
    pd.DataFrame(value_results).set_index("model")[["r2_log"]].plot.bar(ax=axes[1], rot=0, color="#2a9d8f")
    axes[1].set_title("Model B — Market Value (R² on log salary)"); axes[1].set_ylim(0, 1)
    fig.tight_layout(); fig.savefig(REPORTS_DIR / "model_comparison.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=LEVELS, yticklabels=LEVELS, ax=ax)
    ax.set_xlabel("Predicted level"); ax.set_ylabel("Actual level"); ax.set_title("Confusion matrix (test set)")
    fig.tight_layout(); fig.savefig(REPORTS_DIR / "confusion_matrix.png", dpi=130); plt.close(fig)

    for name, imp in [("level", imp_level), ("value", imp_value)]:
        fig, ax = plt.subplots(figsize=(7, 6))
        pd.Series(imp).sort_values().plot.barh(ax=ax, color="#264653")
        ax.set_title(f"Top features — {'Level Classifier' if name == 'level' else 'Market Value'}")
        fig.tight_layout(); fig.savefig(REPORTS_DIR / f"feature_importance_{name}.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.5, 5))
    sample = np.random.default_rng(0).choice(len(y_test_value), size=min(4000, len(y_test_value)), replace=False)
    ax.scatter(np.asarray(y_test_value)[sample], pred_value[sample], s=4, alpha=0.3)
    ax.plot([0, 400_000], [0, 400_000], color="red", lw=1)
    ax.set_xlim(0, 400_000); ax.set_ylim(0, 400_000)
    ax.set_xlabel("Actual salary (USD)"); ax.set_ylabel("Predicted salary (USD)")
    ax.set_title("Market Value: predicted vs actual")
    fig.tight_layout(); fig.savefig(REPORTS_DIR / "predicted_vs_actual.png", dpi=130); plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="fewer trees, for a quick test run")
    args = parser.parse_args()

    df = pd.read_parquet(CLEAN_FILE)
    print(f"Loaded {len(df):,} clean rows from {CLEAN_FILE.name}")

    meta = build_meta(df)
    X = build_features(df, meta)
    y_level = df["level"].map({lvl: i for i, lvl in enumerate(LEVELS)})   # Junior=0 ... Lead=3
    y_value = df["salary_usd"]
    print(f"Feature matrix: {X.shape[0]:,} rows x {X.shape[1]} columns")

    # 80% train / 20% test, same rows for both models. stratify keeps level proportions equal.
    idx_train, idx_test = train_test_split(
        df.index, test_size=0.2, random_state=RANDOM_STATE, stratify=y_level)
    X_train, X_test = X.loc[idx_train], X.loc[idx_test]

    level_models, level_results, best_level = train_level_models(
        X_train, X_test, y_level.loc[idx_train], y_level.loc[idx_test], args.fast)
    value_models, value_results, best_value = train_value_models(
        X_train, X_test, y_value.loc[idx_train], y_value.loc[idx_test], args.fast)

    level_model = level_models[best_level]
    value_model = value_models[best_value]

    level_pred = level_model.predict(X_test)
    cm = confusion_matrix(y_level.loc[idx_test], level_pred)
    print("\nClassification report (best level model):")
    print(classification_report(y_level.loc[idx_test], level_pred, target_names=LEVELS, digits=3))
    value_pred = np.exp(value_model.predict(X_test))

    imp_level = feature_importance(level_model, X.columns)
    imp_value = feature_importance(value_model, X.columns)

    meta.update({
        "level_model": best_level,
        "value_model": best_value,
        "level_results": level_results,
        "value_results": value_results,
        "confusion_matrix": cm.tolist(),
        "feature_importance_level": imp_level,
        "feature_importance_value": imp_value,
        "skill_stats": skill_stats_by_role(df, meta["skills"]),
        "skill_popularity": df["skills"].str.split(";").explode().value_counts()
                              .reindex(meta["skills"]).fillna(0).astype(int).to_dict(),
        "education_levels": EDUCATION_LEVELS,
        "train_rows": int(len(idx_train)),
        "test_rows": int(len(idx_test)),
        "level_salary_median": df.groupby("level")["salary_usd"].median().round(0).to_dict(),
        # typical 0-100 level_score of each level, used to turn class probabilities into a score
        "level_score_median": df.groupby("level")["level_score"].median().round(1).reindex(LEVELS).to_list(),
    })

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(level_model, MODELS_DIR / "level_model.joblib")
    joblib.dump(value_model, MODELS_DIR / "value_model.joblib")
    with open(MODELS_DIR / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    save_charts(level_results, value_results, cm, imp_level, imp_value, y_value.loc[idx_test], value_pred)

    print(f"\nSaved models + meta.json to {MODELS_DIR}")
    print(f"Saved charts to {REPORTS_DIR}")

    # STEP 4 + 5: detailed evaluation on the test set, and market trends
    from evaluate import run_evaluation
    from trends import build_trends
    print("\n=== Evaluation ===")
    run_evaluation()
    print("\n=== Market trends ===")
    build_trends()


if __name__ == "__main__":
    main()
