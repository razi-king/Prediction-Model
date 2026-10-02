"""
STEP 5 — Market trends: which skills are growing among professional developers (2021 → 2025)?

    python trends.py          (train.py also runs this automatically)

Input : data/clean.parquet (which was loaded from Cassandra by clean.py)
Output: models/trends.json  -> used by the learning guide ("Rising: 21% → 35% of developers")

How: for every skill, share of developers using it in each survey year.
Some survey questions were not asked every year (e.g. the 2025 survey dropped the
"Misc tech" question with NumPy/Pandas), so for each skill we compare the FIRST and LAST
year in which it was actually asked (share > 0).
"""
import json

import pandas as pd

from config import CLEAN_FILE, MODELS_DIR


def build_trends():
    df = pd.read_parquet(CLEAN_FILE)
    with open(MODELS_DIR / "meta.json", encoding="utf-8") as f:
        skills = json.load(f)["skills"]

    dummies = df["skills"].str.get_dummies(sep=";").reindex(columns=skills, fill_value=0)
    share = dummies.groupby(df["survey_year"]).mean()          # rows = years, cols = skills

    trends = {}
    for skill in skills:
        s = share[skill]
        asked = s[s > 0.002]
        if len(asked) < 2:
            continue
        first_year, last_year = int(asked.index[0]), int(asked.index[-1])
        first, last = float(asked.iloc[0]), float(asked.iloc[-1])
        change = last - first
        relative = change / first if first else 0
        if change >= 0.03 or (relative >= 0.3 and last >= 0.03):
            label = "rising"
        elif change <= -0.03 or (relative <= -0.3 and first >= 0.03):
            label = "declining"
        else:
            label = "stable"
        trends[skill] = {
            "trend": label,
            "first_year": first_year, "last_year": last_year,
            "first_share": round(first, 3), "last_share": round(last, 3),
            "change_pts": round(change * 100, 1),
            "by_year": {int(y): round(float(v), 3) for y, v in s.items()},
        }

    # AI tools: "Do you use AI tools in your development process?" (asked 2023-2025)
    ai = df.dropna(subset=["uses_ai"]) if "uses_ai" in df.columns else df.iloc[0:0]
    ai_by_year = {int(y): round(float(v), 3) for y, v in ai.groupby("survey_year")["uses_ai"].mean().items()}

    rising = sorted((k for k, v in trends.items() if v["trend"] == "rising"),
                    key=lambda k: trends[k]["change_pts"], reverse=True)
    declining = sorted((k for k, v in trends.items() if v["trend"] == "declining"),
                       key=lambda k: trends[k]["change_pts"])
    out = {"skills": trends, "top_rising": rising[:12], "top_declining": declining[:8], "ai_usage_by_year": ai_by_year}
    with open(MODELS_DIR / "trends.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    print("Top rising skills (share of professional developers, first -> last year):")
    for k in rising[:12]:
        t = trends[k]
        print(f"  {k:<28} {t['first_share']:.0%} ({t['first_year']}) -> {t['last_share']:.0%} ({t['last_year']})")
    print("Top declining:", ", ".join(declining[:8]))
    print("AI tool usage by year:", {y: f"{v:.0%}" for y, v in ai_by_year.items()})
    print(f"Saved {MODELS_DIR / 'trends.json'}")


if __name__ == "__main__":
    build_trends()
