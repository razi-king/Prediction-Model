"""
STEP 2 — Read raw survey rows from Cassandra, clean them, create the level labels.

    python clean.py                 # read from Cassandra (normal way)
    python clean.py --source csv    # read the CSV files directly (backup if Cassandra is down)

Output: ml/data/clean.parquet  (one row per developer, ready for training)

Cleaning steps (each one is printed with the number of rows left):
  1. keep professional developers who are employed and reported a salary
  2. remove salary outliers (< $3k or > $600k per year)
  3. convert experience text to numbers ("Less than 1 year" -> 0)
  4. map the many DevType answers to ~15 simple roles
  5. merge all technology columns into one clean skill list
  6. create the target label: Junior / Mid / Senior / Lead
"""
import argparse

import numpy as np
import pandas as pd

from config import CLEAN_FILE, KEYSPACE, LEVELS, MAX_SALARY, MIN_SALARY, SKILL_COLUMNS, SURVEY_YEARS
from features import combine_skills, education_to_number, normalize_role, years_to_number


# ---------------- Loading ----------------
def load_from_cassandra() -> pd.DataFrame:
    from cassandra.query import SimpleStatement

    from cassandra_db import connect

    cluster, session = connect()
    session.set_keyspace(KEYSPACE)
    frames = []
    for year in SURVEY_YEARS:
        # One partition per year -> efficient query. fetch_size = rows per network page.
        query = SimpleStatement("SELECT * FROM survey_responses WHERE survey_year = %s", fetch_size=5000)
        rows = list(session.execute(query, (year,), timeout=120))
        frames.append(pd.DataFrame(rows))
        print(f"  loaded {len(rows):,} rows for {year} from Cassandra")
    cluster.shutdown()
    return pd.concat(frames, ignore_index=True)


def load_from_csv() -> pd.DataFrame:
    from ingest import read_year

    frames = [read_year(y) for y in SURVEY_YEARS]
    return pd.concat(frames, ignore_index=True)


# ---------------- Cleaning ----------------
def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    print(f"Start: {len(df):,} rows")

    # 1. professional developers with a job and a salary
    df = df[df["main_branch"].fillna("").str.contains("developer by profession")]
    df = df[df["employment"].fillna("").str.contains("Employed|Independent", regex=True)]
    df = df[df["salary_usd"].notna()]
    print(f"  professional + employed + has salary: {len(df):,}")

    # 2. salary outliers
    df = df[(df["salary_usd"] >= MIN_SALARY) & (df["salary_usd"] <= MAX_SALARY)]
    print(f"  salary between ${MIN_SALARY:,} and ${MAX_SALARY:,}: {len(df):,}")

    # 3. experience text -> numbers
    df["years_code"] = df["years_code"].map(years_to_number)
    df["years_pro"] = df["years_code_pro"].map(years_to_number)
    df = df.dropna(subset=["years_code", "years_pro"])
    df = df[df["years_pro"] <= 50]
    # you can't have more professional years than total coding years
    df["years_code"] = np.maximum(df["years_code"], df["years_pro"])
    print(f"  valid experience: {len(df):,}")

    # 4. role
    df["role"] = df["dev_type"].map(normalize_role)
    df = df.dropna(subset=["role"])
    print(f"  has a developer role: {len(df):,}")

    # 5. education + skills
    df["ed_level"] = df["ed_level"].map(education_to_number)
    df["skills"] = df[list(SKILL_COLUMNS.keys())].apply(combine_skills, axis=1)
    df = df[df["skills"] != ""]
    df["country"] = df["country"].fillna("Other")
    print(f"  has at least one skill: {len(df):,}")

    # 6. level label
    df = add_level_label(df)

    # AI usage answer (only asked from 2023) -> True / False / missing. Used for the AI trend.
    if "ai_select" not in df.columns:
        df["ai_select"] = None
    df["uses_ai"] = df["ai_select"].map(
        lambda v: None if not isinstance(v, str) else v.startswith("Yes"))

    keep = ["survey_year", "response_id", "years_code", "years_pro", "ed_level", "role",
            "country", "skills", "salary_usd", "level_score", "level", "uses_ai"]
    return df[keep].reset_index(drop=True)


def add_level_label(df: pd.DataFrame) -> pd.DataFrame:
    """
    The survey has no "Junior/Senior" question, so we DEFINE the level from two facts:
      * experience percentile  — how experienced you are compared with all developers
      * salary percentile      — how well the market pays you compared with developers
                                 in the SAME country and SAME year (fair across countries/inflation)
    level_score = average of the two (0..100). Then:
        bottom 30% -> Junior,  next 30% -> Mid,  next 25% -> Senior,  top 15% -> Lead
    """
    country_counts = df["country"].value_counts()
    big_country = df["country"].where(df["country"].map(country_counts) >= 300, "Other")

    exp_pct = df["years_pro"].rank(pct=True)
    sal_pct = df.groupby([big_country, df["survey_year"]])["salary_usd"].rank(pct=True)
    df["level_score"] = (100 * (exp_pct + sal_pct) / 2).round(2)

    cuts = df["level_score"].quantile([0.30, 0.60, 0.85]).to_list()
    df["level"] = pd.cut(df["level_score"], bins=[-1, *cuts, 101], labels=LEVELS).astype(str)
    print(f"  level cut-offs on level_score: {[round(c, 1) for c in cuts]}")
    print("  level counts:", df["level"].value_counts().reindex(LEVELS).to_dict())
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["cassandra", "csv"], default="cassandra")
    args = parser.parse_args()

    print(f"Loading raw data from {args.source}...")
    raw = load_from_cassandra() if args.source == "cassandra" else load_from_csv()
    df = clean(raw)
    CLEAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(CLEAN_FILE, index=False)
    print(f"Saved {len(df):,} clean rows -> {CLEAN_FILE}")
    print(df.groupby("level")[["years_pro", "salary_usd"]].median().reindex(LEVELS).round(0))


if __name__ == "__main__":
    main()
