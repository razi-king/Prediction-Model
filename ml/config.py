"""
Shared settings for the ML pipeline (paths, Cassandra connection, constants).
Every other script imports from here so that settings live in ONE place.
"""
import os
from pathlib import Path

# ---------- Paths ----------
ML_DIR = Path(__file__).resolve().parent
DATA_DIR = ML_DIR / "data"
RAW_DIR = DATA_DIR / "raw"                 # put survey_YYYY.csv files here
CLEAN_FILE = DATA_DIR / "clean.parquet"    # output of clean.py
MODELS_DIR = ML_DIR / "models"             # output of train.py
REPORTS_DIR = MODELS_DIR / "reports"       # charts for the project report

# ---------- Cassandra ----------
CASSANDRA_HOSTS = os.getenv("CASSANDRA_HOSTS", "127.0.0.1").split(",")
CASSANDRA_PORT = int(os.getenv("CASSANDRA_PORT", "9042"))
KEYSPACE = os.getenv("CASSANDRA_KEYSPACE", "devascend")

# Cloud Cassandra (DataStax Astra DB) for deployment. Leave these EMPTY to use the
# local Docker Cassandra. When ASTRA_DB_TOKEN is set, the code connects to Astra instead.
ASTRA_DB_TOKEN = os.getenv("ASTRA_DB_TOKEN", "")                         # "AstraCS:..."
ASTRA_DB_SECURE_BUNDLE = os.getenv("ASTRA_DB_SECURE_BUNDLE", "")         # path to secure-connect-*.zip
ASTRA_DB_SECURE_BUNDLE_B64 = os.getenv("ASTRA_DB_SECURE_BUNDLE_B64", "") # same zip as base64 text (for hosting secrets)

# ---------- Data ----------
SURVEY_YEARS = [2021, 2022, 2023, 2024, 2025]
LATEST_YEAR = max(SURVEY_YEARS)   # used when predicting for a user "today"

# Survey columns that contain a ";"-separated list of technologies.
SKILL_COLUMNS = {
    "languages": "LanguageHaveWorkedWith",
    "platforms": "PlatformHaveWorkedWith",
    "webframes": "WebframeHaveWorkedWith",
    "databases": "DatabaseHaveWorkedWith",
    "tools": "ToolsTechHaveWorkedWith",
    "misc_tech": "MiscTechHaveWorkedWith",
}

# Salary sanity limits in USD/year (anything outside is treated as a typo / outlier).
MIN_SALARY = 3_000
MAX_SALARY = 600_000

# ---------- Features ----------
TOP_COUNTRIES = 30     # countries outside the top 30 become "Other"
TOP_SKILLS = 100       # only the 100 most common skills become 0/1 columns
LEVELS = ["Junior", "Mid", "Senior", "Lead"]

# ---------- Growth simulator ----------
HOURS_PER_SKILL = 80   # assumed study hours to become productive in one new skill
MAX_SIM_MONTHS = 120   # simulate at most 10 years ahead
RANDOM_STATE = 42
