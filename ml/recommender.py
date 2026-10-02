"""
Learning Guide — a HYBRID recommender for "what should I learn next?"

The survey data only knows ~100 technologies. It knows nothing about things like
Tailwind, form validation, Git workflow, system design or AI-assisted coding, which are
exactly what juniors struggle to discover. So we combine three sources:

  1. KNOWLEDGE BASE  (knowledge/learning_topics.json, hand-written)
     ~50 topics with prerequisites, roles, typical level, why it matters, free resources.
     -> "You know HTML/CSS  =>  Tailwind CSS is unlocked"
  2. ML MODELS       (what-if engine in predictor.py)
     -> "Docker: +21% market value according to the model"
  3. MARKET DATA     (trends.json from 5 years of survey data)
     -> "TypeScript: 34% -> 44% of professional developers"

Scoring (higher = recommend first):
  +3    topic is a CORE skill of your role (core_for), +1 if merely relevant to your role
  +2    'essential' workplace skill and you are Junior/Mid (the things nobody tells you)
  +1.5  rising in the survey data   (+1 if rising according to the knowledge base only)
  -1    declining in the survey data
  +0..3 market value boost from the ML what-if engine
  +0.5  topic is typically learned at your current level
"""
import json

from config import LEVELS, ML_DIR, MODELS_DIR

KB_FILE = ML_DIR / "knowledge" / "learning_topics.json"


class LearningGuide:
    def __init__(self, kb_file=KB_FILE, trends_file=MODELS_DIR / "trends.json"):
        with open(kb_file, encoding="utf-8") as f:
            self.topics = json.load(f)["topics"]
        try:
            with open(trends_file, encoding="utf-8") as f:
                self.trends = json.load(f)
        except FileNotFoundError:
            self.trends = {"skills": {}, "top_rising": [], "top_declining": [], "ai_usage_by_year": {}}
        self.by_id = {t["id"]: t for t in self.topics}
        self.by_skill = {t["survey_skill"]: t for t in self.topics if t["survey_skill"]}
        self.by_name = {t["name"]: t for t in self.topics}

    # Names the user can pick in the form that the ML model does not know (Tailwind CSS, GraphQL...)
    def extra_skill_names(self) -> list[str]:
        return [t["name"] for t in self.topics if not t["survey_skill"] and t["type"] == "skill"]

    def topic_for(self, skill: str):
        """Find the knowledge-base topic for a survey skill name, topic id or topic name."""
        return self.by_skill.get(skill) or self.by_id.get(skill) or self.by_name.get(skill)

    def resources_for(self, skill: str) -> list[dict]:
        topic = self.topic_for(skill)
        return topic["resources"] if topic else []

    # ------------------------------------------------------------------
    def _known(self, user_skills: set) -> set:
        """Everything the user knows: their skills + ids/names of topics that match those skills."""
        known = set(user_skills)
        for t in self.topics:
            if t["name"] in user_skills or (t["survey_skill"] and t["survey_skill"] in user_skills):
                known.add(t["id"])
                known.add(t["name"])
        return known

    def _trend_reason(self, topic):
        skill = topic["survey_skill"]
        data = self.trends["skills"].get(skill) if skill else None
        if data:
            text = (f"{data['first_share']:.0%} → {data['last_share']:.0%} of professional developers "
                    f"({data['first_year']}→{data['last_year']})")
            if data["trend"] == "rising":
                return 1.5, f"Rising in the survey data: {text}", "rising"
            if data["trend"] == "declining":
                return -1.0, f"Declining in the survey data: {text}", "declining"
            return 0.0, None, "stable"
        if topic["category"] == "AI" and self.trends["ai_usage_by_year"]:
            years = sorted(self.trends["ai_usage_by_year"].items())
            (y0, v0), (y1, v1) = years[0], years[-1]
            return 1.5, f"AI tool use among developers grew from {v0:.0%} ({y0}) to {v1:.0%} ({y1})", "rising"
        if topic["trend"] == "rising":
            return 1.0, "Growing demand in job listings and new projects", "rising"
        return 0.0, None, topic["trend"]

    def recommend(self, profile: dict, level: str, what_if: list[dict], top_next=8, top_essentials=6) -> dict:
        user_skills = set(profile.get("skills", []))
        known = self._known(user_skills)
        level_idx = LEVELS.index(level)
        boosts = {w["skill"]: w for w in what_if}

        scored = []
        for t in self.topics:
            if t["id"] in known:
                continue
            # 1) prerequisites: need at least ONE of requires_any
            matched = [r for r in t["requires_any"] if r in known]
            if t["requires_any"] and not matched:
                continue
            # 2) role and level filters
            if "*" not in t["roles"] and profile["role"] not in t["roles"]:
                continue
            t_idx = LEVELS.index(t["level"])
            if t_idx > level_idx + 1:          # too advanced for now (e.g. Kubernetes for a Junior)
                continue

            score, reasons = 1.0, []
            if matched:
                names = [self.by_id[m]["name"] if m in self.by_id else m for m in matched[:2]]
                reasons.append(f"You know {' and '.join(names)} → this is a natural next step")
            if profile["role"] in t.get("core_for", []):
                score += 3
                reasons.append(f"Core skill for {profile['role']} developers")
            elif "*" not in t["roles"]:
                score += 1
                reasons.append(f"Useful for {profile['role']} developers")
            if t["type"] == "essential" and level_idx <= 1:
                score += 2
                reasons.append("Juniors usually only learn this at their first job, so learning it early puts you ahead")
            trend_pts, trend_reason, trend_label = self._trend_reason(t)
            score += trend_pts
            if trend_reason:
                reasons.append(trend_reason)
            boost = boosts.get(t["survey_skill"]) if t["survey_skill"] else None
            if boost:
                score += min(boost["impact"] / 10, 3)
                reasons.append(f"ML model: +{boost['salary_boost_pct']:.1f}% market value for your profile")
            if t_idx == level_idx:
                score += 0.5
            elif t_idx == level_idx + 1:
                reasons.append(f"Prepares you for {LEVELS[t_idx]} level")

            scored.append({
                "id": t["id"], "name": t["name"],
                # name the ML model understands (survey skill) or the topic name if the survey doesn't have it
                "model_skill": t["survey_skill"] or t["name"], "category": t["category"], "type": t["type"],
                "level": t["level"], "hours": t["hours"], "why": t["why"], "learn": t["learn"],
                "resources": t["resources"], "trend": trend_label,
                "score": round(score, 2), "reasons": reasons,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        next_skills = [s for s in scored if s["type"] != "essential"][:top_next]
        essentials = [s for s in scored if s["type"] == "essential"][:top_essentials]

        rising = []
        for skill in self.trends["top_rising"][:8]:
            d = self.trends["skills"][skill]
            rising.append({"skill": skill, "from": d["first_share"], "to": d["last_share"],
                           "from_year": d["first_year"], "to_year": d["last_year"],
                           "you_have_it": skill in user_skills})
        return {
            "next_skills": next_skills,
            "essentials": essentials,
            "market": {"rising": rising, "declining": self.trends["top_declining"][:6],
                       "ai_usage_by_year": self.trends["ai_usage_by_year"]},
        }

    def learning_path(self, profile: dict, level: str, what_if: list[dict], steps=8, max_essentials=3) -> list[dict]:
        """
        Ordered learning plan that follows the prerequisite graph (a "skill tree").
        Greedy: pick the best topic, pretend you learned it (which can UNLOCK new topics,
        e.g. React -> Next.js), pick again ... until `steps` topics are chosen.
        At most `max_essentials` workplace essentials so the plan stays mostly technical.
        """
        known = list(profile.get("skills", []))
        path, essentials = [], 0
        for _ in range(steps):
            rec = self.recommend({**profile, "skills": known}, level, what_if, top_next=50, top_essentials=50)
            options = rec["next_skills"] + (rec["essentials"] if essentials < max_essentials else [])
            if not options:
                break
            best = max(options, key=lambda t: t["score"])
            path.append(best)
            essentials += best["type"] == "essential"
            known.append(best["model_skill"])
            known.append(best["name"])
        return path
