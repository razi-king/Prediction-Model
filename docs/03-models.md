# 3. Models A and B

## Features (`ml/features.py → build_features`)
Each developer becomes **151 numbers**:

| Group | Count | Encoding |
|---|---|---|
| years_code, years_pro, ed_level, survey_year, num_skills | 5 | numbers |
| role | 15 | **one-hot** (role_Full-stack = 1, others 0) |
| country (top 30 + "Other") | 31 | one-hot |
| skills (100 most common) | 100 | **multi-hot** (1 if the developer uses it) |

The same function is used by **training and the API**, so a user's profile is encoded exactly like the training data. The vocabulary (which countries and skills) is saved in `models/meta.json`.

## Train/test split
`train_test_split(test_size=0.2, stratify=level, random_state=42)` gives **122,916 training** and **30,729 test** developers.
- *Stratify* keeps the same Junior/Mid/Senior/Lead proportions in both parts.
- The **same split** is used for all six models, so the comparison is fair.
- The test set is never seen during training, which measures how well the model works on new people.

---

## Model A: Level Classifier (classification)
Predicts **Junior / Mid / Senior / Lead**.

| Algorithm | How it works (one line) |
|---|---|
| Logistic Regression | Weighted sum of features turned into probabilities with softmax; a linear baseline. Features are scaled first with StandardScaler. |
| Random Forest | 150 decision trees, each trained on a random sample of rows and features; they vote (bagging). |
| XGBoost | Trees built **one after another**, each fixing the errors of the previous ones (gradient boosting). |

### Results (test set)
| Algorithm | Accuracy | F1 (macro) | Within ±1 level |
|---|---|---|---|
| Logistic Regression | 62.2% | 0.603 | 97.9% |
| Random Forest | 63.3% | 0.623 | 97.9% |
| **XGBoost** ✅ | **65.2%** | **0.646** | **97.9%** |

Per class (XGBoost): Junior F1 0.82, Mid 0.58, Senior 0.54, Lead 0.64.

**Metrics explained**
- **Accuracy** is the share of predictions that are exactly right. Random guessing gets 25%.
- **F1 (macro)**: F1 is the balance of precision and recall for one class. Macro means the average over the 4 classes, so the small Lead class counts as much as the big Junior class. We choose the best model by F1.
- **Within ±1 level**: 97.9% of predictions are the correct level or a neighbouring one. Big mistakes (Junior predicted as Lead) almost never happen.
- **Confusion matrix** (`models/reports/confusion_matrix.png`): rows are the true level and columns the predicted level. Most errors are between neighbours (Mid↔Senior), which makes sense because the levels are cut-offs on a continuous scale.

**Why not 90% accuracy?** Two developers with the same profile can be paid very differently (company, negotiation, city). The survey doesn't contain those factors, so some error is unavoidable.

### Score 0–100
The classifier outputs a probability for each level. The score is the probability-weighted typical level_score of each level:
`score = P(Junior)·20 + P(Mid)·48 + P(Senior)·68.2 + P(Lead)·84.7`.
These numbers are the median level_score of each level in the data.

---

## Model B: Market Value Regressor (regression)
Predicts **yearly salary in USD**. We use it as a measurable stand-in for "how much the market values your skills".

We train on **log(salary)** because salaries are very skewed (a few very high values). Log makes the distribution close to a bell curve, so big salaries don't dominate the errors. Predictions are converted back with `exp()`.

| Algorithm | R² (log) | R² ($) | MAE | RMSE |
|---|---|---|---|---|
| Linear Regression | 0.584 | 0.393 | $31,089 | $56,327 |
| Random Forest | 0.633 | 0.463 | $28,401 | $52,959 |
| **XGBoost** ✅ | **0.649** | **0.482** | **$27,810** | **$52,049** |

**Metrics explained**
- **R²**: the share of the variation in salary that the model explains. 1 is perfect and 0 is as good as always predicting the average. 0.65 on log salary is strong for survey salary data.
- **MAE**: the average absolute error in dollars.
- **RMSE**: like MAE, but big errors count more because they are squared.

**XGBoost monotone constraint**: we tell XGBoost that salary may only go **up** when experience goes up (`monotone_constraints` on years_code and years_pro). This uses domain knowledge and makes the growth curve logical.

## Feature importance (`models/reports/feature_importance_*.png`)
- **Level model**: years_pro dominates, followed by skills like PHP (lower pay), AWS, Kubernetes and Terraform, and roles Manager/Architect.
- **Value model**: **country** dominates (USA, India, Switzerland…), then experience, then skills.

## Saved files (`ml/models/`)
| File | Content |
|---|---|
| level_model.joblib | the trained XGBoost classifier |
| value_model.joblib | the trained XGBoost regressor |
| meta.json | vocabulary, feature columns, all metrics, skill statistics per role/level |
| reports/*.png | comparison chart, confusion matrix, feature importance, predicted vs actual |
| training_log.txt | console output of the last training run |
