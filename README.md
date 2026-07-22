# NBA Franchise Fan Revenue Intelligence Engine

**Role:** Embedded Data & Strategy Function (Business Analyst · Data Analyst · Data Scientist · Strategy Consultant · AI Engineer — one seat)
**Sport:** NBA Basketball
**Modeled on:** Pacers Sports & Entertainment's June 2025 Salesforce Agentforce / Data Cloud / Marketing Cloud deployment, which unified 30+ previously siloed fan data sources (ticketing, mobile app, F&B, retail, chatbot) into one connected ecosystem. The Indiana Fever (their WNBA team) used this architecture to set franchise records in 2024: a 265% attendance increase, record ticket sales, and record digital engagement.

## The strategic question this project answers

> Which fans are at risk of churning, which seats should we price up for next Saturday's game, and which sponsor package should we go to market with in Q3 — all based on live data as of today?

## Why this project exists

Every Business Analyst, Data Analyst, or Strategy Consultant role at an NBA franchise, a consulting firm advising sports clients, or a sports-tech vendor expects this exact skillset. The sports fan engagement platform market is valued at $4.8B in 2025, growing at 11.9% CAGR to $13.2B by 2034. This project builds the full BA lifecycle end-to-end — from stakeholder interviews to a board deck with a revenue number attached — on a synthetic dataset with deliberately realistic data quality issues, because real Salesforce CRM, Ticketmaster POS, and arena F&B data is proprietary.

## Tech stack

| Layer | Tools |
|---|---|
| Warehouse | **DuckDB** (local, free — swapped in for Snowflake to avoid trial-account cost/expiry; same dbt models, same architecture pattern) |
| Transformation | dbt (dbt-duckdb) |
| Orchestration | Apache Airflow |
| Real-time streaming | Kafka (local, via Docker Compose) |
| Data generation | Python + Faker |
| Data profiling | ydata-profiling, KNIME |
| ML | XGBoost, LightGBM, SHAP, Prophet, scikit-learn, lifelines (survival analysis) |
| BI | Power BI Desktop |
| Apps | Streamlit |
| AI layer | Claude API (natural-language fan insights co-pilot) |

## Project structure

```
nba-fan-revenue-engine/
├── data/                  # synthetic + profiled datasets
├── dbt_project/           # dbt-duckdb models (staging/intermediate/marts)
├── dags/                  # Airflow DAG
├── notebooks/             # EDA, ML training
├── models/                # trained ML models + SHAP outputs
├── streamlit_app/         # Matchday Ops Center + Fan Insights Co-Pilot
├── sql/                   # standalone query library (30+ queries)
├── docs/                  # AS-IS doc, BRD, DQ report, memos, board deck
├── docker-compose.yml     # local Kafka + Zookeeper
└── requirements.txt
```

## Build progress — 10-phase BA lifecycle

- [x] **Phase 0 — Environment setup**: Python 3.11 venv, DuckDB, dbt-duckdb, Docker + local Kafka cluster, full ML stack installed and verified. See [`docs/PHASE_0_SETUP.md`](docs/PHASE_0_SETUP.md).
- [x] **Phase 1 — Discovery (AS-IS State)**: 3 simulated stakeholder interviews (VP Marketing, Director of Ticket Sales, Arena GM), current-state data flow diagram across 5 siloed systems, and a quantified $2.4M cost-of-doing-nothing baseline. See [`docs/AS_IS_State_Document.docx`](docs/AS_IS_State_Document.docx).
- [ ] Phase 2 — Requirements (BRD + acceptance criteria)
- [ ] Phase 3 — Data discovery & profiling
- [ ] Phase 4 — ELT pipeline (Bronze/Silver/Gold on DuckDB, Airflow-orchestrated)
- [ ] Phase 5 — Star schema data modeling
- [ ] Phase 6 — Descriptive analysis (RFM segmentation, 30+ SQL queries)
- [ ] Phase 7 — 5 ML models: churn prediction, dynamic pricing, CLV, concessions forecasting, sponsor audience scoring
- [ ] Phase 8 — Power BI semantic model + 4 dashboards (CEO, Ticket Sales, Pricing, Sponsorship)
- [ ] Phase 9 — Real-time matchday operations center (Kafka + Streamlit)
- [ ] Phase 10 — Stakeholder delivery: executive memo, board deck, live app, Claude API co-pilot, resume bullet

## Headline business outcome (target)

Identification of **~$2.4M** in at-risk season-ticket revenue, with a fan-by-fan intervention recommendation driven by a churn model and CLV-weighted prioritization — plus a dynamic pricing backtest quantifying the matchday revenue left on the table under the current pricing process.

## Getting started

See [`docs/PHASE_0_SETUP.md`](docs/PHASE_0_SETUP.md) for full Windows setup instructions (Python, DuckDB, Docker/Kafka, Power BI). Quick version:

```powershell
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
docker compose up -d
```
