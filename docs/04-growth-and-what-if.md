# 4. Growth simulator, what-if engine, skill gaps, roadmap
Code: `ml/predictor.py` (class `DevAscendPredictor`)

## Model C: Growth Simulator
This isn't a separately trained model. It is **logic on top of Models A and B**.

```
for month m = 0 … 120:
    profile_m.years_code = years_code + m/12
    profile_m.years_pro  = years_pro  + m/12
    skills learned so far = floor(m / months_per_skill) skills from the plan
    → ask Model A (level probabilities) and Model B (salary)
```
- Each planned skill takes **its own study hours** from the knowledge base (e.g. Tailwind 15 h, React 60 h). Skills not in the knowledge base use the default of 80 h (`config.HOURS_PER_SKILL`). At 10 h/week you study about 43 h per month, and skills are learned one after another.
- **Two scenarios** are simulated: *experience only* (no new skills) and *with roadmap*. The chart shows both lines, and the gap between them is the value of learning.
- All 121 months are predicted in **one batch**, which is fast (about 1 s for a full analysis).

### Two smoothing tricks
1. **Interpolation between whole years.** The survey records whole years, so the tree models only change their answer at year boundaries. For 2.25 years we predict at 2 and 3 years and mix them 75%/25%, which gives a smooth monthly curve.
2. **Running maximum.** Gaining experience shouldn't make you worse, so each month's value is at least the previous month's value. This removes small zig-zags caused by the tree models.

### Time to goal
- **Level goal**: the first month where the model is ≥ 50% sure you are at the goal level or above, i.e. `P(goal) + P(levels above) ≥ 0.5`.
- **Salary goal**: the first month where predicted salary ≥ target.
- If the goal isn't reached within 10 years, we show "not within 10 years".

## Skill gap analysis
From the training data we computed, **for each role and level**, the share of developers who use each skill (`meta.json → skill_stats`).
For you: we take your role and levels **above** your predicted level, and list skills that ≥ 10% of those developers use and you don't. They're sorted by how common they are and how big the jump is from your level.
The UI shows a bar for the share at higher levels and a tick mark for the share at your level.

## What-if engine
1. Candidates are skills you don't have that at least 5% of Senior/Lead developers in your role use.
2. For each candidate we **switch it on** in your profile and re-predict with both models.
3. We measure the market value change (%) and the level score change.
4. `impact = (value % + score change) × (0.5 + share of seniors who use it)`. The weight stops rare niche tools from beating widely-used skills.
5. For the top 8 skills we also simulate *"learn only this skill"* against *"learn nothing"* and report **how many months sooner** you reach the goal.

This is a simple form of **model explanation**. It works like SHAP: "what happens to the prediction if this feature changes?"

## Roadmap
The roadmap now comes from the **learning guide** (see `docs/09-learning-guide.md`). It's a path through a prerequisite skill tree, ranked by role, ML market-value boost and market trends. Each step lists what to learn and **free resources** with links.
The growth chart's "with roadmap" line uses **exactly this plan**.

## Honest limitations (good to mention in viva)
- **Cross-sectional data**: we don't see real people over time; the simulation assumes you'll look like developers who already have more experience.
- **Correlation, not causation**: "Kafka users earn more" may partly be because Kafka is used at big, well-paying companies.
- **Salary as a skill proxy**: pay also depends on company, city and negotiation, which aren't in the data.
- **Study hours per topic** are estimates from the knowledge base, not learned from data.
- Skills that only exist in the knowledge base (Tailwind, validation…) don't change the ML prediction, because the survey has no data about them.
