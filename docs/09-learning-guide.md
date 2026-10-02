# 9. Learning guide: "what should I learn next?"
Code: `ml/recommender.py` (class `LearningGuide`), knowledge base `ml/knowledge/learning_topics.json`, trends `ml/trends.py`.
UI: `web/components/LearningGuide.jsx`, plus the resource links inside `Roadmap.jsx`.

## The problem
The survey data only knows about 100 technologies, like React, Docker and AWS. It knows nothing about things juniors struggle to discover:
- **Tailwind CSS** (not in the survey)
- **Form validation**, server-side validation, error handling
- **Git team workflow**: pull requests, merge conflicts
- Environment variables and secrets, debugging, testing, security
- **System design**
- **AI-assisted development** and building LLM features

An ML model can't recommend something it has never seen in the data. So DevAscend uses a **hybrid recommender** that combines three sources.

## The 3 sources
| Source | What it gives | Example |
|---|---|---|
| **Knowledge base** (hand-written JSON, 52 topics) | prerequisites, role, typical level, why it matters, what to learn, **free resources** | "Tailwind CSS needs HTML/CSS → unlocked for you" |
| **ML models** (what-if engine) | predicted market value boost for your exact profile | "Docker: +21% market value" |
| **Market data** (`trends.json`, from the 5 survey years loaded from Cassandra) | is the skill rising or falling? | "TypeScript: 38% → 50% of developers" |

A **hybrid recommender** combines **knowledge-based** recommendation (rules and expert knowledge) with **data-driven** recommendation (ML and statistics). This is a standard approach when data alone doesn't cover everything. It's also called the *cold-start* problem: there is no data for Tailwind or validation.

## Knowledge base topic (example)
```json
{
  "id": "tailwind", "name": "Tailwind CSS", "survey_skill": null,
  "category": "Frontend", "type": "skill", "level": "Junior",
  "requires_any": ["HTML/CSS"], "roles": ["Front-end", "Full-stack", "Other"],
  "hours": 15, "trend": "rising",
  "why": "You already know CSS. Tailwind lets you style much faster...",
  "learn": ["Utility classes", "Responsive prefixes", "..."],
  "resources": [{"title": "Tailwind CSS official docs", "url": "https://tailwindcss.com/docs", "type": "docs"}]
}
```
- `requires_any`: you need at least one of these. It can be a survey skill name or another topic id. This makes the topics a **prerequisite graph** (skill tree): HTML/CSS → Tailwind, JavaScript → React → Next.js, Docker → Kubernetes.
- `type`:
  - `skill`: a technology
  - `essential`: a workplace skill that tutorials skip
  - `trend`: where the market is going (system design, AI)
- `survey_skill` links the topic to the ML data when the survey knows it. That gives an ML boost and a trend from real data.
- All resources are **free** official docs, courses or YouTube channels. All 100+ links were checked automatically.

## The algorithm (`LearningGuide.recommend`)
1. **What do you know?** Your skills, plus the topics they correspond to.
2. **Filter** the topics:
   - skip what you already know
   - prerequisites must be met (at least one of `requires_any`)
   - the topic must fit your role (or be for every role, `*`)
   - the topic must not be too advanced: at most one level above your predicted level, so a Junior doesn't get Kubernetes
3. **Score** each remaining topic:
   | Rule | Points |
   |---|---|
   | a CORE skill of your role (`core_for`, e.g. ML fundamentals for Data/ML) | +3 |
| relevant to your role (but not core) | +1 |
   | "essential" workplace skill and you are Junior/Mid | +2 |
   | rising in survey data (or knowledge base says rising) | +1.5 (+1) |
   | declining in survey data | −1 |
   | ML market value boost (what-if impact ÷ 10, max 3) | +0 … +3 |
   | typically learned at your current level | +0.5 |
4. **Sort by score** and return:
   - **next_skills**: the top 8 technologies and trends
   - **essentials**: the top 6 "things juniors learn too late"
   - **market**: the fastest-rising skills and AI tool adoption by year
5. Every recommendation has **reasons** that explain it. For example: "You know HTML/CSS → this is a natural next step", "Rising in the survey data: 38% → 50%", "ML model: +8% market value".

## Example: a Junior Front-end developer who knows HTML/CSS, JavaScript and React
The guide recommends:
- **TypeScript**, **Tailwind CSS**, React and Next.js as next skills
- **form validation**, **Git team workflow**, **testing**, **debugging** and **environment variables/secrets** as essentials
- **AI-assisted development** as a trend, because AI tool use grew from 43% (2023) to 81% (2025) of professional developers according to the survey data

## Learning roadmap = a path through the skill tree (`LearningGuide.learning_path`)
The month-by-month roadmap is built **greedily**:
1. Pick the highest-scoring topic.
2. Pretend you've learned it. This can **unlock** new topics (React → Next.js).
3. Pick again, until there are 8 topics. At most 3 of them are workplace essentials.

Each topic takes **its own study hours** from the knowledge base (Tailwind ≈ 15 h, React ≈ 60 h, AWS ≈ 40 h). At 10 h/week that's about 43 h per month.
The growth simulation uses the same plan. Skills the survey knows (TypeScript, React, Docker…) change the ML prediction once they're finished. Knowledge-base-only skills (Tailwind, validation…) take study time but can't change the prediction, because the model has no data about them.

Example roadmaps (1 year of experience, 10 h/week):
| Role & skills | Roadmap |
|---|---|
| Front-end: HTML/CSS, JS | TypeScript → Tailwind CSS → React → Next.js → Form validation → Accessibility → Testing → SQL |
| Back-end: Java, SQL | Redis → Go → REST API design → PostgreSQL → Docker → System design → Server-side validation → DB design |
| Data/ML: Python, Pandas, SQL | LLM features → PostgreSQL → ML fundamentals → Testing → Git workflow → Env/secrets → Linux → Docker |
| Mobile: Kotlin, Java | Docker → REST API design → HTML/CSS → Form validation → Flutter → SwiftUI → Auth → SQL |

## Market trends (`ml/trends.py`)
- For each skill, we compute the share of professional developers using it in each survey year.
- We compare the first and last year the question was asked. This matters because 2025 dropped the "Misc tech" question.
- **Rising** means +3 percentage points, or +30% relative with at least 3% usage. **Declining** is the opposite.
- Real results (2021 → 2025): TypeScript 38% → 50%, Python 41% → 54%, PostgreSQL 41% → 50%, Docker 54% → 62%, Go 11% → 18%, Rust 6% → 14%, FastAPI 3% → 12%. Declining: jQuery, Heroku, MySQL, .NET Framework, Angular.
- Note: if the survey reworded an answer between years (e.g. "Bash/Shell" became "Bash/Shell (all shells)"), part of the change may come from the wording.
- **AI adoption** comes from the survey question "Do you use AI tools in your development process?" (`AISelect`, asked 2023–2025). It is stored in Cassandra as the `ai_select` column. Result: **43% (2023) → 63% (2024) → 81% (2025)** of professional developers use AI tools.

## Viva questions
**Q: Why not just use ML for recommendations?**
ML can only recommend what is in its training data. Tailwind, validation and system design aren't survey answers. The knowledge base fills that gap, and ML plus trend data rank what *is* in the data. Combining them is a hybrid recommender.

**Q: How do you make sure recommendations fit the user?**
Prerequisites (you must know HTML/CSS before Tailwind), role filters, and a level filter (no Senior topics for Juniors). The scoring also favours workplace essentials for Juniors.

**Q: Isn't the knowledge base just your opinion?**
Partly, and we say so. It's expert knowledge from official documentation and roadmaps. Where the survey has data, the ranking uses real numbers (trend and ML boost) instead of opinion. The knowledge base is a plain JSON file, so it's easy to review and extend.
