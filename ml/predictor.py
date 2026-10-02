"""
Model C (Growth Simulator) + What-if Engine, built ON TOP of the two trained models.

No public dataset follows the same developers over many years. So instead we:
  1. learn from 150k developers who are at DIFFERENT career stages (Models A and B), then
  2. SIMULATE one user moving forward in time: every month we add 1/12 year of experience
     and (depending on study hours) the next planned skill, and ask the models again.

Used by the FastAPI backend (api/main.py) and usable directly from Python:
    from predictor import DevAscendPredictor
    p = DevAscendPredictor()
    p.predict({...profile...})
"""
import json
import math

import joblib
import numpy as np

from config import HOURS_PER_SKILL, LATEST_YEAR, MAX_SIM_MONTHS, MODELS_DIR
from features import SKILL_ALIASES, build_features, profiles_to_frame
from recommender import LearningGuide

CHECKPOINTS = [0, 6, 12, 24, 36]          # months shown as cards on the dashboard
WEEKS_PER_MONTH = 52 / 12


def format_months(months) -> str:
    if months is None:
        return "not within 10 years"
    if months == 0:
        return "already reached"
    years, rest = divmod(int(months), 12)
    parts = []
    if years:
        parts.append(f"{years} year{'s' if years > 1 else ''}")
    if rest:
        parts.append(f"{rest} month{'s' if rest > 1 else ''}")
    return " ".join(parts)


class DevAscendPredictor:
    def __init__(self, models_dir=MODELS_DIR):
        self.level_model = joblib.load(models_dir / "level_model.joblib")
        self.value_model = joblib.load(models_dir / "value_model.joblib")
        with open(models_dir / "meta.json", encoding="utf-8") as f:
            self.meta = json.load(f)
        self.levels = self.meta["levels"]
        self.known_skills = set(self.meta["skills"])
        self.guide = LearningGuide()   # knowledge base + market trends

    # ------------------------------------------------------------------ helpers
    def _prepare(self, profile: dict) -> dict:
        p = dict(profile)
        skills = (SKILL_ALIASES.get(s.strip(), s.strip()) for s in p.get("skills", []))   # "AWS" -> full name
        p["skills"] = sorted({s for s in skills if s in self.known_skills})
        p.setdefault("survey_year", LATEST_YEAR)
        return p

    def _raw_batch(self, profiles: list[dict]):
        X = build_features(profiles_to_frame(profiles), self.meta)
        probs = self.level_model.predict_proba(X)                 # shape (n, 4)
        log_salary = self.value_model.predict(X)                  # model learned log(salary)
        return probs, log_salary

    def _batch(self, profiles: list[dict]):
        """
        Predict many profiles at once (much faster than one by one).

        The survey only records WHOLE years of experience, so the models change their answer
        only when a year boundary is crossed. To get a smooth month-by-month result we predict
        at the two nearest whole years and blend them (linear interpolation).
        Example: 2.25 years = 75% of the prediction at 2 years + 25% of the prediction at 3 years.
        """
        lower, upper, weights = [], [], []
        for p in profiles:
            frac = p["years_pro"] - math.floor(p["years_pro"])
            lower.append({**p, "years_pro": p["years_pro"] - frac, "years_code": p["years_code"] - frac})
            upper.append({**p, "years_pro": p["years_pro"] - frac + 1, "years_code": p["years_code"] - frac + 1})
            weights.append(frac)
        w = np.array(weights)
        if not w.any():   # all whole years -> no blending needed
            probs, log_salary = self._raw_batch(profiles)
        else:
            probs_all, log_all = self._raw_batch(lower + upper)
            n = len(profiles)
            probs = probs_all[:n] * (1 - w[:, None]) + probs_all[n:] * w[:, None]
            log_salary = log_all[:n] * (1 - w) + log_all[n:] * w
        salary = np.exp(log_salary)
        # score 0..100 = probability-weighted typical level_score of each level
        # (e.g. 100% Junior -> 20, 100% Lead -> 85, 50/50 Mid/Senior -> 58)
        score = probs @ np.array(self.meta["level_score_median"])
        return probs, salary, score

    def _goal_reached(self, probs, salary, goal) -> np.ndarray:
        if goal["type"] == "salary":
            return salary >= goal["salary"]
        goal_idx = self.levels.index(goal["level"])
        # reached when the model thinks it is at least 50% likely you are at goal level or above
        return probs[:, goal_idx:].sum(axis=1) >= 0.5

    def _skill_hours(self, skill: str) -> float:
        """Study hours for a skill: from the knowledge base if it has the topic, else the default."""
        topic = self.guide.topic_for(skill)
        return topic["hours"] if topic else HOURS_PER_SKILL

    def _finish_months(self, plan, hours_per_week):
        """Month in which each planned skill is finished (skills are learned one after another)."""
        if hours_per_week <= 0:
            return [math.inf] * len(plan)
        per_month = hours_per_week * WEEKS_PER_MONTH
        finish, total = [], 0.0
        for skill in plan:
            total += self._skill_hours(skill) / per_month
            finish.append(total)
        return finish

    def _timeline(self, profile, plan, hours, months=MAX_SIM_MONTHS):
        """Profile at month 0..months: +1/12 year experience per month, + each planned skill once finished."""
        finish = self._finish_months(plan, hours)
        timeline = []
        for m in range(months + 1):
            p = dict(profile)
            p["years_code"] = profile["years_code"] + m / 12
            p["years_pro"] = profile["years_pro"] + m / 12
            # skills the ML model doesn't know (e.g. "Tailwind CSS") take study time but don't change the prediction
            p["skills"] = list(profile["skills"]) + [s for s, f in zip(plan, finish) if f <= m]
            timeline.append(p)
        return timeline

    def _simulate(self, profile, plan, hours, goal):
        probs, salary, score = self._batch(self._timeline(profile, plan, hours))
        # A developer does not get worse by gaining experience, so we keep the running maximum
        # (smooths small ups and downs that come from the tree models' step-like predictions).
        salary = np.maximum.accumulate(salary)
        score = np.maximum.accumulate(score)
        reached = np.maximum.accumulate(self._goal_reached(probs, salary, goal).astype(int)).astype(bool)
        month = int(np.argmax(reached)) if reached.any() else None
        return probs, salary, score, month

    # ------------------------------------------------------------------ /predict
    def predict(self, profile: dict) -> dict:
        p = self._prepare(profile)
        probs, salary, score = self._batch([p])
        idx = int(np.argmax(probs[0]))
        # 80% range: on the test set, 80% of real salaries were between low_factor x and
        # high_factor x the prediction (computed in evaluate.py)
        interval = self.meta.get("salary_interval", {"low_factor": 1, "high_factor": 1})
        return {
            "level": self.levels[idx],
            "score": round(float(score[0]), 1),
            "probabilities": {lvl: round(float(v), 3) for lvl, v in zip(self.levels, probs[0])},
            "salary_usd": round(float(salary[0]), -2),
            "salary_range": {
                "low": round(float(salary[0]) * interval["low_factor"], -2),
                "high": round(float(salary[0]) * interval["high_factor"], -2),
                "confidence": 0.8,
            },
            "confidence": round(float(probs[0][idx]), 3),
            "known_skills_used": p["skills"],
        }

    # ------------------------------------------------------------------ /analysis
    def skill_gaps(self, profile: dict, top: int = 12) -> list[dict]:
        """Skills common among higher-level developers in your role that you don't have yet."""
        p = self._prepare(profile)
        current = self.predict(p)["level"]
        stats = self.meta["skill_stats"].get(p["role"]) or self.meta["skill_stats"]["Other"]
        cur_idx = self.levels.index(current)
        higher = [lvl for lvl in self.levels[cur_idx + 1:] if lvl in stats] or [self.levels[-1]]
        mine = set(p["skills"])
        gaps = []
        for skill in self.meta["skills"]:
            if skill in mine:
                continue
            target_share = float(np.mean([stats[lvl].get(skill, 0) for lvl in higher]))
            current_share = stats.get(current, {}).get(skill, 0)
            if target_share >= 0.10:
                gaps.append({
                    "skill": skill,
                    "target_share": round(target_share, 3),     # % of higher-level devs who use it
                    "your_level_share": round(current_share, 3),
                    "gap": round(target_share - current_share, 3),
                })
        gaps.sort(key=lambda g: (g["target_share"] + g["gap"]), reverse=True)
        return gaps[:top]

    def what_if(self, profile: dict, hours: float, goal: dict, top: int = 8) -> list[dict]:
        """Turn each missing skill ON, re-predict, and rank skills by how much they help."""
        p = self._prepare(profile)
        stats = self.meta["skill_stats"].get(p["role"]) or self.meta["skill_stats"]["Other"]
        senior_share = {s: max(stats.get("Senior", {}).get(s, 0), stats.get("Lead", {}).get(s, 0))
                        for s in self.meta["skills"]}
        # candidates: skills that at least 5% of senior/lead devs in this role use
        candidates = [s for s in self.meta["skills"] if s not in p["skills"] and senior_share[s] >= 0.05]
        if not candidates:
            return []

        variants = [p] + [{**p, "skills": p["skills"] + [s]} for s in candidates]
        _, salary, score = self._batch(variants)
        base_salary, base_score = salary[0], score[0]
        results = []
        for i, skill in enumerate(candidates, start=1):
            salary_pct = (salary[i] - base_salary) / base_salary * 100
            results.append({
                "skill": skill,
                "salary_boost_pct": round(float(salary_pct), 2),
                "score_boost": round(float(score[i] - base_score), 2),
                "senior_share": round(senior_share[skill], 3),
            })
        # impact = (market value % + level score points), weighted by how common the skill is among
        # senior developers in your role -> avoids recommending rare niche tools first
        for r in results:
            r["impact"] = round((r["salary_boost_pct"] + r["score_boost"]) * (0.5 + r["senior_share"]), 2)
        results = [r for r in results if r["salary_boost_pct"] > 0 or r["score_boost"] > 0]
        results.sort(key=lambda r: r["impact"], reverse=True)
        results = results[:top]

        # How much sooner would you reach the goal if you learned ONLY this skill first?
        _, _, _, base_month = self._simulate(p, [], hours, goal)
        for r in results:
            _, _, _, month = self._simulate(p, [r["skill"]], hours, goal)
            if base_month is None or month is None:
                r["months_sooner"] = None if month is None else MAX_SIM_MONTHS - month
            else:
                r["months_sooner"] = base_month - month
        return results

    def roadmap(self, path: list[dict], hours: float) -> list[dict]:
        """
        Month-by-month plan from the learning guide's skill-tree path (see recommender.learning_path).
        Each topic takes its own study hours from the knowledge base (Tailwind ~15 h, AWS ~40 h).
        """
        if hours <= 0:
            return []
        keys = [item["model_skill"] for item in path]
        finish = self._finish_months(keys, hours)
        plan, start = [], 0.0
        for item, end in zip(path, finish):
            plan.append({
                "skill": item["model_skill"],      # name used by the ML model / growth simulation
                "name": item["name"],              # name shown to the user
                "category": item["category"],
                "type": item["type"],
                "start_month": int(start) + 1,
                "end_month": max(int(math.ceil(end)), int(start) + 1),
                "hours": item["hours"],
                "why": "; ".join(item["reasons"][:3]) or item["why"],
                "steps": item["learn"],
                "resources": item["resources"],
            })
            start = end
        return plan

    def analysis(self, profile: dict, hours: float, goal: dict) -> dict:
        gaps = self.skill_gaps(profile)
        boosts = self.what_if(profile, hours, goal)
        level = self.predict(profile)["level"]
        # the guide also sees skills the ML model doesn't know (e.g. "Tailwind CSS")
        all_skills = [SKILL_ALIASES.get(s.strip(), s.strip()) for s in profile.get("skills", [])]
        full_profile = {**profile, "skills": all_skills}
        guide = self.guide.recommend(full_profile, level, boosts)
        path = self.guide.learning_path(full_profile, level, boosts)
        return {"skill_gaps": gaps, "what_if": boosts, "roadmap": self.roadmap(path, hours), "guide": guide}

    # ------------------------------------------------------------------ /growth
    def growth(self, profile: dict, hours: float, goal: dict, plan: list[str] | None = None) -> dict:
        p = self._prepare(profile)
        if plan is None:   # default plan = the roadmap skills
            plan = [step["skill"] for step in self.analysis(p, hours, goal)["roadmap"]]
        # keep every planned skill: survey skills change the prediction, knowledge-base-only
        # skills (Tailwind, validation...) still take study time in the simulation
        plan = [SKILL_ALIASES.get(s, s) for s in plan]
        plan = [s for s in dict.fromkeys(plan) if s not in p["skills"]]

        probs_e, salary_e, score_e, month_e = self._simulate(p, [], hours, goal)    # experience only
        probs_p, salary_p, score_p, month_p = self._simulate(p, plan, hours, goal)  # experience + plan

        curve = []
        for m in range(0, 37):
            curve.append({
                "month": m,
                "score_experience_only": round(float(score_e[m]), 1),
                "score_with_plan": round(float(score_p[m]), 1),
                "salary_experience_only": round(float(salary_e[m]), -2),
                "salary_with_plan": round(float(salary_p[m]), -2),
            })
        checkpoints = []
        for m in CHECKPOINTS:
            checkpoints.append({
                "month": m,
                "label": "Now" if m == 0 else (f"{m} months" if m < 12 else f"{m // 12} year{'s' if m > 12 else ''}"),
                "level": self.levels[int(np.argmax(probs_p[m]))],
                "score": round(float(score_p[m]), 1),
                "salary_usd": round(float(salary_p[m]), -2),
            })
        goal_text = goal["level"] if goal["type"] == "level" else f"${goal['salary']:,.0f}/year"
        return {
            "plan": plan,
            "curve": curve,
            "checkpoints": checkpoints,
            "time_to_goal": {
                "goal": goal_text,
                "months_with_plan": month_p,
                "months_experience_only": month_e,
                "text_with_plan": format_months(month_p),
                "text_experience_only": format_months(month_e),
                "summary": (
                    f"At {hours:g} hrs/week you'll reach {goal_text} in ~{format_months(month_p)}"
                    if month_p else f"{goal_text} is not reached within 10 years in this simulation"
                ),
            },
        }
