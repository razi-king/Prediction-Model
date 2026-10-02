# DevAscend: Viva Notes

Read these in order. Each file explains one part of the project in simple words, including **what** each part does, **why** it was built that way, and **where** the code is.

| # | File | What it covers |
|---|---|---|
| 1 | [01-overview.md](01-overview.md) | The problem, the idea, the full pipeline in one picture |
| 2 | [02-data-and-cassandra.md](02-data-and-cassandra.md) | Dataset, Cassandra tables, cleaning steps, how the level label is made |
| 3 | [03-models.md](03-models.md) | Model A (classifier) and Model B (regressor), the algorithms compared, metrics |
| 4 | [04-growth-and-what-if.md](04-growth-and-what-if.md) | Model C growth simulator, what-if engine, skill gaps, roadmap |
| 5 | [05-backend-api.md](05-backend-api.md) | FastAPI endpoints, request/response examples |
| 6 | [06-frontend.md](06-frontend.md) | Next.js pages and components, reusable Form/Input |
| 7 | [07-viva-questions.md](07-viva-questions.md) | Likely viva questions with short answers |
| 8 | [08-accuracy-and-errors.md](08-accuracy-and-errors.md) | Accuracy, MAE, RMSE, R², % error: how far predictions are from real data |
| 9 | [09-learning-guide.md](09-learning-guide.md) | Hybrid recommender: knowledge base + ML + market trends, learning resources |
| 10 | [10-deployment.md](10-deployment.md) | Free deployment: Vercel (website), Hugging Face Spaces (API), Astra DB (Cassandra) |

**Key numbers to remember**
- 360,519 raw survey responses (5 years: 2021–2025) stored in Cassandra
- 153,645 developers after cleaning → 122,916 train / 30,729 test (80/20)
- 151 input features (5 numeric + 15 roles + 31 countries + 100 skills)
- Level classifier (XGBoost): **65.2% accuracy**, **97.9% within one level**
- Market value regressor (XGBoost): **R² = 0.649** (log salary), MAE ≈ **$27.8k**, RMSE ≈ **$52.0k**, median error **25.5%**
- Baselines (no ML): 30% level accuracy, MAE $49.2k, so the models clearly beat guessing
- Learning guide: **52 topics** with free resources; AI tool use **43% → 81%** (2023→2025)
