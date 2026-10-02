"""
STEP 1 — Load the raw Stack Overflow survey CSVs into Cassandra.

    python ingest.py

Reads ml/data/raw/survey_<year>.csv for every year in config.SURVEY_YEARS,
keeps only the columns we need, maps them to ONE common schema and inserts
them into the Cassandra table `devascend.survey_responses`.

Why a common schema? The survey changes a little every year. Example: 2025
renamed "YearsCodePro" to "WorkExp" and moved Docker from "ToolsTech" to "Platform".
We store all years in the same table so later steps don't care about the year.
"""
import math
import time

import pandas as pd
from cassandra.concurrent import execute_concurrent_with_args

from cassandra_db import connect, create_schema
from config import RAW_DIR, SKILL_COLUMNS, SURVEY_YEARS

# survey column name -> our Cassandra column name
BASE_COLUMNS = {
    "ResponseId": "response_id",
    "MainBranch": "main_branch",
    "Employment": "employment",
    "Country": "country",
    "EdLevel": "ed_level",
    "YearsCode": "years_code",
    "YearsCodePro": "years_code_pro",
    "WorkExp": "years_code_pro",          # 2025 name for professional experience
    "DevType": "dev_type",
    "ConvertedCompYearly": "salary_usd",
    "AISelect": "ai_select",               # "do you use AI tools?" (asked from 2023)
}
SKILL_RENAME = {survey_col: our_col for our_col, survey_col in SKILL_COLUMNS.items()}
TEXT_COLUMNS = [
    "main_branch", "employment", "country", "ed_level", "years_code", "years_code_pro",
    "dev_type", *SKILL_COLUMNS.keys(), "ai_select",
]

INSERT_CQL = f"""
INSERT INTO survey_responses (survey_year, response_id, {", ".join(TEXT_COLUMNS)}, salary_usd)
VALUES ({", ".join(["?"] * (len(TEXT_COLUMNS) + 3))})
"""


def read_year(year: int) -> pd.DataFrame:
    path = RAW_DIR / f"survey_{year}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Download the survey CSV (see README).")

    header = pd.read_csv(path, nrows=0, encoding="utf-8-sig").columns
    wanted = {**BASE_COLUMNS, **SKILL_RENAME}
    # 2024 and earlier have YearsCodePro; ignore WorkExp there (it means something else).
    if "YearsCodePro" in header:
        wanted.pop("WorkExp")
    usecols = [c for c in wanted if c in header]

    df = pd.read_csv(path, usecols=usecols, encoding="utf-8-sig", low_memory=False, dtype=str)
    df = df.rename(columns=wanted)
    for col in TEXT_COLUMNS:                      # columns a year doesn't have -> empty
        if col not in df.columns:
            df[col] = None
    df["survey_year"] = year
    df["response_id"] = df["response_id"].astype(int)
    df["salary_usd"] = pd.to_numeric(df["salary_usd"], errors="coerce")
    return df


def to_rows(df: pd.DataFrame):
    """Convert a DataFrame into plain Python tuples in the INSERT column order."""
    cols = ["survey_year", "response_id", *TEXT_COLUMNS, "salary_usd"]
    for record in df[cols].itertuples(index=False, name=None):
        yield tuple(
            None if (isinstance(v, float) and math.isnan(v)) else v
            for v in record
        )


def main():
    print("Connecting to Cassandra...")
    cluster, session = connect()
    create_schema(session)
    insert = session.prepare(INSERT_CQL)   # prepared once, executed many times (fast)

    total = 0
    for year in SURVEY_YEARS:
        start = time.time()
        df = read_year(year)
        results = execute_concurrent_with_args(
            session, insert, list(to_rows(df)), concurrency=100, raise_on_first_error=True
        )
        ok = sum(1 for success, _ in results if success)
        total += ok
        print(f"  {year}: inserted {ok:,} rows in {time.time() - start:.1f}s")

    # Count per partition (one year at a time). A COUNT(*) over the whole table is a full
    # cluster scan, which Cassandra handles badly — querying by partition key is the Cassandra way.
    count = sum(
        session.execute("SELECT COUNT(*) FROM survey_responses WHERE survey_year = %s", (year,), timeout=120).one()[0]
        for year in SURVEY_YEARS
    )
    print(f"Done. Inserted {total:,} rows. Table now holds {count:,} rows.")
    cluster.shutdown()


if __name__ == "__main__":
    main()
