# 7. Likely viva questions (with short answers)

### About the project
**Q: What does your project do?**
It predicts a developer's current level and market value, then simulates their growth over time to estimate when they'll reach their goal and which skills to learn next.

**Q: Where does the data come from?**
The Stack Overflow Developer Survey, 2021–2025. That's 360,519 real responses; 153,645 remain after cleaning.

**Q: Which kind of ML problem is it?**
Two supervised problems: **classification** (level, 4 classes) and **regression** (salary). The growth simulator and what-if engine are logic built on top of them.

**Q: The survey has no "level" column. Where do the labels come from?**
We defined them: level_score = the average of the experience percentile and the salary percentile within the same country and year. It's then cut into Junior (bottom 30%), Mid (next 30%), Senior (next 25%) and Lead (top 15%).

**Q: Isn't the label partly made from experience, which is also an input?**
Yes, partly. That's why the classifier isn't trivially perfect: the salary half of the label must be learned from skills, role, country and education. It's a deliberate choice, because seniority really is a mix of experience and market value.

### Data and Cassandra
**Q: Why Cassandra and not MySQL?**
Cassandra is a distributed NoSQL database built for large write-heavy data and horizontal scaling. We store 360k survey rows and every prediction the app makes. Its partition-key design gives fast queries for our access patterns: all rows of a year, and the latest predictions.

**Q: What is a partition key?**
The part of the primary key that decides which node stores the row. Rows with the same partition key are stored together, so reading one partition is fast. Ours is `survey_year`.

**Q: Can you do JOINs in Cassandra?**
No. You design one table per query ("query-first" modelling) and denormalise the data.

**Q: How did you clean the data?**
Kept employed professional developers with a salary. Removed salaries outside $3k–$600k. Converted text years to numbers. Mapped 30+ job types to 15 roles. Merged and de-duplicated skills, fixing spelling differences between years. See `docs/02`.

**Q: Why log(salary)?**
Salaries are right-skewed. Log makes the distribution symmetric, so a few very high salaries don't dominate training, and errors become relative (percent) instead of absolute.

**Q: What is one-hot / multi-hot encoding?**
Turning categories into 0/1 columns. A role is one-hot (exactly one column is 1). Skills are multi-hot (many columns can be 1).

### Models
**Q: Why compare 3 algorithms?**
To pick the best one with evidence. Logistic and Linear Regression are simple linear baselines. Random Forest is bagging (many independent trees voting). XGBoost is boosting (trees built one after another to fix errors).

**Q: Why did XGBoost win?**
Boosting captures non-linear effects and interactions (e.g. Kubernetes is worth more in some countries and roles) and handles many sparse 0/1 features well.

**Q: Explain the difference between bagging and boosting.**
Bagging trains trees **in parallel** on random samples and averages them, which reduces variance. Boosting trains trees **one after another**, each focusing on the previous trees' errors, which reduces bias.

**Q: What is the train/test split and why stratify?**
80% of the data is used to learn and 20% (never seen) to evaluate. Stratify keeps the class proportions the same in both parts.

**Q: Explain accuracy, precision, recall and F1.**
- Accuracy is the share of correct predictions.
- Precision answers: of everyone predicted Senior, how many really are?
- Recall answers: of all real Seniors, how many did we find?
- F1 is the harmonic mean of precision and recall.
- Macro F1 averages over classes equally.

**Q: Explain R², MAE and RMSE.**
- R² is the share of variance explained (1 = perfect).
- MAE is the average absolute error in dollars.
- RMSE is the square root of the mean squared error, so it penalises big errors more.

**Q: 65% accuracy seems low?**
It's 4 classes, so random guessing gets 25%. 97.9% of predictions are within one level, and most errors are between neighbouring levels. Salary also depends on things the survey doesn't record (company, city, negotiation), which puts a ceiling on accuracy.

**Q: What is overfitting and how did you prevent it?**
Overfitting is when a model memorises the training data and fails on new data. We prevented it by:
- limiting tree depth and requiring at least 5 samples per leaf
- using row and column subsampling
- using a learning rate in XGBoost
- evaluating on an unseen test set

**Q: What is a monotone constraint?**
We told XGBoost that predicted salary can only increase with experience. It's domain knowledge that keeps the growth curve logical.

**Q: How do you explain predictions?**
In three ways:
- feature importance from the tree models
- the what-if engine, which switches a skill on and measures the change (a similar idea to SHAP)
- the per-level probabilities shown in the UI

### Growth simulation
**Q: How do you predict the future without data that follows people over time?**
We use cross-sectional data. We learn from developers at all stages, then simulate the user month by month (more experience, plus new skills based on study hours) and re-predict each month.

**Q: Why is the curve smooth if the survey has whole years?**
We interpolate between the predictions at the two nearest whole years, and keep a running maximum because experience can't make you worse.

**Q: How is the time to goal computed?**
It's the first simulated month where P(level ≥ goal) ≥ 50%, or where predicted salary ≥ the target salary.

**Q: Limitations?**
- Correlation is not causation.
- Salary is only a proxy for skill.
- 80 hours per skill is an assumption.
- Survey respondents aren't a perfect sample of all developers.

### Backend and frontend
**Q: Why FastAPI?**
It's fast, validates requests automatically with Pydantic, generates interactive docs at /docs, and is Python, so it shares code with the ML part (`features.py`).

**Q: Why are the models loaded at startup?**
Loading the .joblib files takes time. Loading them once and keeping them in memory makes each request fast (about 1 second for a full analysis).

**Q: What is CORS?**
A browser security rule. The website (port 3000) may call the API (port 8000) only if the API allows that origin.

**Q: What are reusable components?**
`Form` and `Input` are written once and used for every field. This means less code and consistent behaviour. Props make them configurable (label, type, options, error).

**Q: How does the frontend talk to the backend?**
With `fetch()` calls in `lib/api.js`, sending JSON. Independent calls run in parallel with `Promise.all`.

### Accuracy and recommendations (see docs/08 and docs/09 for more)
**Q: What are MAE and RMSE for your model?**
MAE is $27,810 and RMSE is $52,049, against a baseline of $49,222 and $74,183 when always predicting the median. The median % error is 25.5%, and 80% of real salaries fall inside our predicted range.

**Q: How does your model recommend Tailwind if Tailwind is not in the data?**
Through a hybrid recommender. A knowledge base of 52 topics with prerequisites (HTML/CSS → Tailwind) handles skills the data doesn't have. The ML what-if engine and 5 years of survey trends rank the skills it does have.

**Q: What is a hybrid recommender?**
A combination of knowledge-based recommendation (rules and expert knowledge) and data-driven recommendation (ML and statistics). It solves the cold-start problem for topics without data.

**Q: How do you know AI skills matter?**
From the survey data stored in Cassandra: AI tool use among professional developers went from 43% (2023) to 63% (2024) to 81% (2025).

### Future work
- Collect real data that follows developers over time.
- Add city and company size.
- Add SHAP explanations.
- Use per-skill learning time.
- Add user accounts.
- Deploy Cassandra as a 3-node cluster with replication factor 3.

### 3D design
**Q: How did you make the 3D interface?**
With Three.js (WebGL). `components/Scene3D.jsx` draws a wireframe crystal, orbit rings, a particle field, rising "growth" particles and a grid floor behind the page, with mouse parallax. Three.js is loaded only in the browser, inside `useEffect`. The animation pauses when the tab is hidden and respects reduce-motion. If WebGL is disabled, a pure-CSS version is shown instead.

**Q: Doesn't 3D slow the page down?**
The canvas is limited to a pixel ratio of 2. The scene is small: a few meshes and about 2,600 points in two buffers. It stops rendering when the tab isn't visible, and the canvas has `pointer-events: none`, so it never blocks the form.
