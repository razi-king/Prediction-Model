# 8. Accuracy and errors: how far are predictions from the real data?
Code: `ml/evaluate.py` (it runs automatically at the end of `train.py`)
Output: `ml/models/evaluation.json`, `ml/models/reports/error_distribution.png`, `confusion_matrix_pct.png`
Website: the **Model accuracy** page (`/accuracy`), and the API endpoint `GET /evaluation`

All numbers come from the **30,729 test developers** (20%) that the models **never saw** during training. We compare each prediction with what that developer **actually** reported in the survey.

---

## Model A: Level classifier (XGBoost)

| Metric | Value | Meaning |
|---|---|---|
| **Accuracy** | **65.2%** | predicted exactly the right level |
| Baseline accuracy | 30.0% | always guessing the most common level (no ML) |
| **F1 (macro)** | **0.646** | balance of precision & recall, averaged over the 4 levels |
| **Within ±1 level** | **97.9%** | right level or a neighbouring one |
| Off by 2+ levels | 2.1% | big mistakes (e.g. Junior predicted as Senior) |
| Mean level error | 0.37 | on average the prediction is 0.37 levels away |

### Confusion matrix (% of each real level)
| actual ↓ / predicted → | Junior | Mid | Senior | Lead |
|---|---|---|---|---|
| **Junior** | **83%** | 17% | 1% | 0% |
| **Mid** | 18% | **58%** | 21% | 3% |
| **Senior** | 1% | 27% | **54%** | 19% |
| **Lead** | 0% | 3% | 32% | **65%** |

**How to read it:** the diagonal shows correct predictions. Almost all mistakes are **one level away**, which is expected because the levels are cut-offs on a continuous score. Mid and Senior are hardest because they sit in the middle, with neighbours on both sides.

### Precision, recall, F1 per level
| Level | Precision | Recall | F1 |
|---|---|---|---|
| Junior | 81.2% | 82.6% | 0.819 |
| Mid | 58.9% | 57.6% | 0.582 |
| Senior | 54.3% | 53.7% | 0.540 |
| Lead | 63.4% | 65.0% | 0.642 |

- **Precision**: when the model says "Senior", how often it's right.
- **Recall**: of all real Seniors, how many the model found.
- **F1**: the harmonic mean of precision and recall, `2·P·R / (P+R)`.

---

## Model B: Market value regressor (XGBoost)

| Metric | Value | Baseline (always predict the median salary) |
|---|---|---|
| **R² (log salary)** | **0.649** | 0 |
| R² (dollars) | 0.482 | 0 |
| **MAE**: mean absolute error | **$27,810** | $49,222 |
| Median absolute error | $15,451 | |
| **RMSE**: root mean squared error | **$52,049** | $74,183 |
| **MAPE**: mean absolute % error | 46.0% | |
| **Median % error** | **25.5%** | |
| Within ±10% of real salary | 21.2% | |
| Within ±20% of real salary | 40.6% | |
| Within ±30% of real salary | 56.2% | |
| Bias (mean of predicted − actual) | −$8,192 | slightly under-predicts on average |

### Formulas (for the viva)
```
error_i = predicted_i − actual_i
MAE   = average of |error_i|                     → typical miss in dollars
RMSE  = sqrt( average of error_i² )              → big misses count more (squared)
MAPE  = average of |error_i| / actual_i × 100    → miss in percent
R²    = 1 − Σ error_i² / Σ (actual_i − mean)²    → share of salary differences explained
Bias  = average of error_i                       → + over-predicts, − under-predicts
```
- **Why RMSE > MAE:** RMSE squares the errors, so a few very big misses (salaries of $300k+) push it up. A large gap between RMSE and MAE means there are some large outliers.
- **Why median % error (25.5%) is much smaller than MAPE (46%):** MAPE is pulled up by very low salaries. Missing a $5,000 salary by $5,000 is a 100% error. The median is the "typical developer" number.
- **Why R² on log salary (0.649) is higher than R² in dollars (0.482):** the model was trained on log salary. In dollars, a few very high salaries dominate the squared errors.

### Errors by real salary band
| Real salary | Developers | Avg real | Avg predicted | MAE | Median % error |
|---|---|---|---|---|---|
| < $25k | 4,774 | $13,469 | $24,229 | $12,527 | 58% |
| $25k–50k | 5,730 | $38,183 | $44,675 | $13,842 | 27% |
| $50k–100k | 10,786 | $73,103 | $74,085 | $19,513 | 21% |
| $100k–150k | 5,253 | $123,619 | $115,033 | $30,429 | 21% |
| > $150k | 4,186 | $224,129 | $151,082 | $82,455 | 27% |

**Regression to the mean:** very low salaries are over-predicted and very high salaries are under-predicted. The survey doesn't know the company, city, or how well someone negotiated, so the model pulls extreme cases toward the average. It is most accurate for typical salaries ($50k–150k, about 21% median error).

### Errors by country (median % error)
USA 21%, Germany 19%, UK 25%, India 40%, Canada 22%, France 21%, Brazil 36%, Poland 27%.
Salaries in India and Brazil vary more (startups vs multinationals), so relative errors are bigger there.

### Errors by level
Junior MAE $14,028 · Mid $25,634 · Senior $32,686 · Lead $51,629. Dollar errors grow with salary, but the **% error stays about 22–28%** for every level.

---

## Uncertainty range (80% prediction interval)
A single number hides uncertainty, so the predictor also shows a **range**:
```
On the test set, the ratio  actual / predicted  was:
  10th percentile = 0.575     90th percentile = 1.783
=> 80% of real salaries are between 0.575× and 1.783× the prediction
```
For example, if the prediction is $20,000/yr, the likely range is **$11,500 – $35,700**. We checked it: exactly **80.0%** of test developers fall inside their range. The range is wider above the prediction because salaries are right-skewed.

This is shown as "likely $X – $Y" under the market value, and the API returns it as `salary_range`.

---

## Viva questions
**Q: What is the difference between MAE and RMSE?**
Both measure the average error in dollars. RMSE squares errors before averaging, so large errors count much more. Our RMSE ($52k) is much higher than MAE ($28k), which tells us there are some big misses on very high salaries.

**Q: Is 65% accuracy good?**
Guessing gives 30%, so the model is more than twice as good. 97.9% of predictions are within one level, and only 2.1% are off by two or more.

**Q: How do you know the model isn't overfitting?**
All numbers are on a test set the model never saw. The training and test accuracies are close, and simple baselines are clearly beaten.

**Q: Why is salary hard to predict?**
Pay depends on things the survey doesn't record: company size and type, city, negotiation, benefits. Even two identical profiles can differ a lot. That's why we show a range, not only one number.

**Q: How could you improve it?**
- add city and company size
- add per-country models
- tune hyper-parameters with cross-validation (GridSearchCV)
- use quantile regression for better uncertainty ranges
