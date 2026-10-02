"""
Feature engineering shared by training (train.py) AND the API (api/predictor.py).

Keeping it in one file guarantees that a user's profile is turned into numbers
in EXACTLY the same way as the training data was. (If the two differed, the
model would receive inputs it never saw during training -> wrong predictions.)

A "profile" is a plain dict like:
    {
      "years_code": 6, "years_pro": 3, "role": "Full-stack",
      "country": "India", "ed_level": 4,          # 0..6, see EDUCATION_LEVELS
      "skills": ["JavaScript", "React", "Node.js"], "survey_year": 2025
    }
"""
import re

import numpy as np
import pandas as pd

# ---------------- Education (text -> ordered number) ----------------
EDUCATION_LEVELS = {
    0: "Primary school",
    1: "Secondary school",
    2: "Some college / other",
    3: "Associate degree",
    4: "Bachelor's degree",
    5: "Master's degree",
    6: "PhD / professional degree",
}


def education_to_number(text) -> int:
    """Survey education answer -> 0..6. Order matters (Master > Bachelor), so we use numbers, not one-hot."""
    if not isinstance(text, str):
        return 2
    t = text.lower()
    if "primary" in t:
        return 0
    if "secondary" in t:
        return 1
    if "associate" in t:
        return 3
    if "bachelor" in t:
        return 4
    if "master" in t:
        return 5
    if "professional" in t or "doctoral" in t or "ph.d" in t:
        return 6
    return 2   # "Some college", "Something else", "Other"


# ---------------- Years of experience (text -> number) ----------------
def years_to_number(value) -> float:
    """'Less than 1 year' -> 0, 'More than 50 years' -> 51, '7' -> 7."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    s = str(value).strip()
    if s.startswith("Less than"):
        return 0.0
    if s.startswith("More than"):
        return 51.0
    try:
        return float(s)
    except ValueError:
        return np.nan


# ---------------- Role (DevType -> one simple category) ----------------
# Developers can tick several job types. We pick ONE using this priority list
# (more specific / more senior roles first).
ROLE_RULES = [
    ("Manager", ["engineering manager", "senior executive", "product manager", "project manager"]),
    ("Architect", ["architect"]),
    ("Data/ML", ["data scientist", "machine learning", "ai/ml", "developer, ai", "applied scientist"]),
    ("Data Engineer", ["data engineer", "database administrator"]),
    ("DevOps/Cloud", ["devops", "cloud infrastructure", "site reliability", "system administrator"]),
    ("Mobile", ["developer, mobile"]),
    ("Embedded", ["embedded", "hardware"]),
    ("Game", ["game or graphics"]),
    ("QA/Test", ["qa or test"]),
    ("Security", ["security"]),
    ("Full-stack", ["full-stack"]),
    ("Back-end", ["back-end"]),
    ("Front-end", ["front-end"]),
    ("Desktop", ["desktop or enterprise"]),
]
ROLES = [name for name, _ in ROLE_RULES] + ["Other"]
EXCLUDED_ROLES = ["student", "retired", "educator", "academic researcher"]


def normalize_role(dev_type) -> str | None:
    """Returns a role from ROLES, or None for people we don't model (students, retired...)."""
    if not isinstance(dev_type, str) or not dev_type.strip():
        return None
    t = dev_type.lower()
    for role, keywords in ROLE_RULES:
        if any(k in t for k in keywords):
            return role
    if any(k in t for k in EXCLUDED_ROLES):
        return None
    return "Other"


# ---------------- Skills ----------------
# Same technology, different spelling in different survey years.
SKILL_ALIASES = {
    "AWS": "Amazon Web Services (AWS)",
    "React.js": "React",
    "Bash/Shell (all shells)": "Bash/Shell",
    "Google Cloud Platform": "Google Cloud",
    "Digital Ocean": "DigitalOcean",
    "ASP.NET CORE": "ASP.NET Core",
    "Dynamodb": "DynamoDB",
    "Angular.js": "AngularJS",
    "Spring Framework": "Spring",
    ".NET (5+)": ".NET",
    ".NET Core / .NET 5": ".NET",
    ".NET Framework (1.0 - 4.8)": ".NET Framework",
    "Scikit-Learn": "Scikit-learn",
    "Torch/PyTorch": "PyTorch",
    "Node.js ": "Node.js",
}
# Package managers, OS installers and hosting brands: they say little about skill
# level and would make silly "learn next" suggestions (e.g. "learn Homebrew").
IGNORED_SKILLS = {
    "Git", "npm", "Yarn", "pnpm", "Pip", "Homebrew", "APT", "Chocolatey", "Pacman", "NuGet",
    "Composer", "Cargo", "Make", "Ninja", "MSBuild", "Visual Studio Solution", "GNU GCC",
    "LLVM's Clang", "Managed Hosting", "OVH", "Hetzner", "Vite", "Webpack", "Maven (build tool)",
    "Gradle", "CMake", "Other", "Other (please specify):", "None of the above", "Podman",
}


def clean_skill(name: str) -> str | None:
    name = name.strip()
    name = SKILL_ALIASES.get(name, name)
    name = re.sub(r"\s+", " ", name)
    if not name or name in IGNORED_SKILLS:
        return None
    return name


def combine_skills(row_values) -> str:
    """Merge several ';'-separated survey columns into one clean, de-duplicated ';' string."""
    skills = set()
    for value in row_values:
        if isinstance(value, str):
            for part in value.split(";"):
                s = clean_skill(part)
                if s:
                    skills.add(s)
    return ";".join(sorted(skills))


# ---------------- Profile(s) -> model input matrix ----------------
NUMERIC_FEATURES = ["years_code", "years_pro", "ed_level", "survey_year", "num_skills"]


def build_features(df: pd.DataFrame, meta: dict) -> pd.DataFrame:
    """
    df needs columns: years_code, years_pro, ed_level, survey_year, role, country, skills (';' string).
    meta holds the vocabulary decided at training time: meta["roles"], meta["countries"], meta["skills"].
    Returns a numeric DataFrame whose columns are ALWAYS meta["feature_columns"] (same order).
    """
    out = pd.DataFrame(index=df.index)
    out["years_code"] = df["years_code"].astype(float)
    out["years_pro"] = df["years_pro"].astype(float)
    out["ed_level"] = df["ed_level"].astype(float)
    out["survey_year"] = df["survey_year"].astype(float)

    # Skills -> one 0/1 column per known skill ("multi-hot encoding")
    skill_dummies = (
        df["skills"].fillna("").astype(str).str.get_dummies(sep=";")
        .reindex(columns=meta["skills"], fill_value=0)
    )
    out["num_skills"] = skill_dummies.sum(axis=1).astype(float)

    # Role and country -> one-hot columns (unknown country -> "Other")
    country = df["country"].where(df["country"].isin(meta["countries"]), "Other")
    role = df["role"].where(df["role"].isin(meta["roles"]), "Other")
    role_dummies = pd.get_dummies(role).reindex(columns=meta["roles"], fill_value=0)
    country_dummies = pd.get_dummies(country).reindex(columns=meta["countries"], fill_value=0)
    role_dummies.columns = [f"role_{c}" for c in role_dummies.columns]
    country_dummies.columns = [f"country_{c}" for c in country_dummies.columns]
    skill_dummies.columns = [f"skill_{c}" for c in skill_dummies.columns]

    X = pd.concat([out, role_dummies, country_dummies, skill_dummies], axis=1).astype(float)
    if "feature_columns" in meta:
        X = X.reindex(columns=meta["feature_columns"], fill_value=0.0)
    return X


def profiles_to_frame(profiles: list[dict]) -> pd.DataFrame:
    """List of profile dicts (from the API) -> DataFrame accepted by build_features."""
    rows = []
    for p in profiles:
        rows.append({
            "years_code": max(float(p["years_code"]), float(p["years_pro"])),
            "years_pro": float(p["years_pro"]),
            "ed_level": int(p["ed_level"]),
            "survey_year": int(p["survey_year"]),
            "role": p["role"],
            "country": p["country"],
            "skills": ";".join(sorted(set(p["skills"]))),
        })
    return pd.DataFrame(rows)
