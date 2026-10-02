# 2. Data and Cassandra

## Dataset
**Stack Overflow Developer Survey**, years **2021, 2022, 2023, 2024 and 2025**. It's a yearly survey of developers worldwide, published under the ODbL open data licence.
Files: `ml/data/raw/survey_<year>.csv` (about 650 MB in total, 360,519 responses).

Columns we use:

| Survey column | Meaning | Our column |
|---|---|---|
| YearsCode | years coding in total (incl. learning) | years_code |
| YearsCodePro (2025: WorkExp) | years coding professionally | years_code_pro |
| DevType | job role(s) | dev_type |
| LanguageHaveWorkedWith | languages | languages |
| PlatformHaveWorkedWith | cloud/platforms (Docker in 2025) | platforms |
| WebframeHaveWorkedWith | web frameworks | webframes |
| DatabaseHaveWorkedWith | databases | databases |
| ToolsTechHaveWorkedWith | tools (Docker, Kubernetes…) | tools |
| MiscTechHaveWorkedWith | libraries (.NET, NumPy, Pandas…) | misc_tech |
| EdLevel | education | ed_level |
| Country | country | country |
| ConvertedCompYearly | yearly salary converted to USD | salary_usd |
| MainBranch, Employment | developer by profession? employed? | filters |
| AISelect (2023+) | do you use AI tools? | ai_select (used for the AI trend) |

**Why combine 5 years?** More data means better models (153k rows instead of about 30k). The survey changes slightly each year, so `ingest.py` maps every year into **one common schema**. For example, 2025 renamed `YearsCodePro` to `WorkExp` and moved Docker into "Platform".

## Cassandra

### What is Cassandra?
Apache Cassandra is a **distributed NoSQL database** (originally built at Facebook). Data is spread across many machines (nodes) with no single master, so it scales horizontally and has no single point of failure. We run one node in Docker (`docker-compose.yml`).

### Key terms
| Term | Meaning | In our project |
|---|---|---|
| Keyspace | like a "database" | `devascend` |
| Replication factor | copies of each row | 1 (single laptop node) |
| Partition key | decides which node stores a row; rows with the same key are stored together | `survey_year` |
| Clustering key | sort order inside a partition | `response_id` / `created_at` |
| CQL | Cassandra Query Language (SQL-like) | `SELECT * FROM survey_responses WHERE survey_year = 2024` |

### Tables (`ml/cassandra_db.py`)
```sql
CREATE TABLE devascend.survey_responses (
    survey_year int, response_id int,
    main_branch text, employment text, country text, ed_level text,
    years_code text, years_code_pro text, dev_type text,
    languages text, platforms text, webframes text, databases text, tools text, misc_tech text, ai_select text,
    salary_usd double,
    PRIMARY KEY ((survey_year), response_id)
);

CREATE TABLE devascend.predictions (
    bucket text, created_at timestamp, id uuid,
    role text, country text, years_pro double, level text, score double,
    salary_usd double, goal text, months_to_goal int, profile_json text,
    PRIMARY KEY ((bucket), created_at, id)
) WITH CLUSTERING ORDER BY (created_at DESC, id ASC);
```

**Query-first design.** In Cassandra you design tables around the queries you will run. There are no JOINs, and you can only filter efficiently by the primary key.
- Training needs "all rows of year X", so the partition key is `survey_year`.
- History needs "latest N predictions", so all predictions go in one partition (`bucket='all'`), sorted by `created_at DESC`. For a large real app we would use one bucket per day or month so a partition doesn't grow forever.

### Loading (`ingest.py`)
- **Prepared statement**: the INSERT is parsed once and reused for every row, which is faster and safe from injection.
- `execute_concurrent_with_args(..., concurrency=100)` sends 100 inserts in parallel. All 360k rows load in about 4 minutes.

### Reading (`clean.py`)
One query per year (one partition each) with `fetch_size=5000`, so the driver downloads rows in pages instead of all at once.

### Counting rows the Cassandra way
`SELECT COUNT(*) FROM survey_responses` without a WHERE scans **every node and every partition**. On a big table it times out. `ingest.py` counts **per partition** instead (`WHERE survey_year = 2021`, 2022, …) and adds the results up.

### Changing the cluster name
Cassandra saves the cluster name in its data folder. When we renamed the project to DevAscend (cluster name `devascend`), the old volume refused to start ("Saved cluster name devgrowth != configured name devascend"). The fix was `docker compose down -v`, which deletes the volume, followed by re-running `ingest.py`. The data is always reproducible from the CSVs.

### Windows note
The Cassandra Python driver needs the `asyncore` module, which Python 3.12+ removed. We install `pyasyncore` (a backport) to fix it.

## Cleaning steps (`clean.py`)
| Step | Rows left |
|---|---|
| Raw (5 years) | 360,519 |
| Professional developers, employed, salary given | 163,791 |
| Salary between $3,000 and $600,000 (outliers/typos removed) | 156,922 |
| Valid experience ("Less than 1 year" → 0, "More than 50 years" → 51) | 155,862 |
| Has a developer role (students, retired, academics removed) | 154,797 |
| At least one skill | **153,645** |

Other transformations:
- **Role**: DevType has 30+ answers and people can tick several. We map them to 15 roles (Full-stack, Back-end, Front-end, Mobile, Data/ML, DevOps/Cloud, Manager, Architect, …) using a priority list (`features.py → ROLE_RULES`).
- **Education** becomes an ordered number from 0 to 6 (Primary=0 … Bachelor=4, Master=5, PhD=6). We use numbers because order matters.
- **Skills**: the 6 technology columns are merged into one list. Spelling differences between years are unified (e.g. "React.js" → "React", "AWS" → "Amazon Web Services (AWS)"). Package managers like npm and Homebrew are ignored because they say little about skill.
- `years_code` is never smaller than `years_pro`.

## The target label: Junior / Mid / Senior / Lead
The survey has **no** "what is your level" question, so we **define** the label from two facts:

```
experience percentile = how experienced you are compared with ALL developers         (0..1)
salary percentile     = how well you're paid compared with developers in the SAME
                        country and SAME survey year (fair across countries/inflation) (0..1)
level_score = 100 × average of the two                                                (0..100)
```
| level_score range | Level | Share | Median years pro | Median salary |
|---|---|---|---|---|
| < 34.9 | Junior | 30% | 3 | $36k |
| 34.9 – 59.2 | Mid | 30% | 7 | $63k |
| 59.2 – 77.7 | Senior | 25% | 12 | $91k |
| ≥ 77.7 | Lead | 15% | 20 | $139k |

**Why the salary percentile is computed inside each country:** a $30k developer in India can be Senior, while $30k in the USA would be Junior. Comparing within each country and year makes the label fair.

## EDA
`ml/notebooks/eda.ipynb` covers rows per year, salary distribution (skewed, which is why we use log), experience vs salary, salary by country, roles, top skills, levels, and which skills are more common at higher levels. The charts are saved in `ml/notebooks/figures/`.
