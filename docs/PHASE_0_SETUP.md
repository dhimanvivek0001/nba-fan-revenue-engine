# Phase 0 — Environment Setup (Windows)

Goal: everything installed and verified before Phase 1 (Discovery). Run these in order.

## 1. Core requirements

| Tool | Purpose | Install |
|---|---|---|
| Python 3.11+ | everything | https://www.python.org/downloads/ — check "Add to PATH" during install |
| Git | version control | https://git-scm.com/download/win |
| Docker Desktop | Kafka + Zookeeper containers | https://www.docker.com/products/docker-desktop/ — needs WSL2 enabled |
| Power BI Desktop | dashboards | Microsoft Store — search "Power BI Desktop", free |
| VS Code (optional but recommended) | editor | https://code.visualstudio.com/ |

Verify after install (open PowerShell):
```powershell
python --version
git --version
docker --version
```

## 2. Clone/create the project folder

```powershell
mkdir C:\projects\nba-fan-revenue-engine
cd C:\projects\nba-fan-revenue-engine
git init
```

Folder structure we'll fill in over the phases:
```
nba-fan-revenue-engine/
├── data/                  # synthetic + profiled datasets
├── dbt_project/           # dbt-duckdb models (staging/intermediate/marts)
├── dags/                  # Airflow DAG
├── notebooks/             # EDA, ML training
├── models/                # trained ML models + SHAP outputs
├── streamlit_app/         # Matchday Ops Center + Fan Insights Co-Pilot
├── sql/                   # standalone query library (30+ queries)
├── docs/                  # AS-IS doc, BRD, DQ report, memos, deck
└── requirements.txt
```

## 3. Python virtual environment

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Verify DuckDB + dbt

```powershell
python -c "import duckdb; print(duckdb.__version__)"
dbt --version
```

## 5. Docker — Kafka local cluster

From the project root:
```powershell
docker compose up -d
docker ps
```
You should see `zookeeper` and `kafka` containers running. This is a real local Kafka broker — we're not simulating it, just running it without a hosted service.

To stop later: `docker compose down`

## 6. Power BI Desktop

Just confirm it opens. We connect it to DuckDB via ODBC in Phase 8 — nothing to configure yet.

## 7. Claude API key

You'll need an API key from console.anthropic.com for Phase 10 (Fan Insights Co-Pilot). Store it as an environment variable, never hardcode it:
```powershell
setx ANTHROPIC_API_KEY "your-key-here"
```

## 8. Airflow (Windows note)

Airflow doesn't run natively on Windows — we'll run it inside a Docker container too (added to docker-compose in Phase 4, not needed yet). Nothing to do here in Phase 0.

---

**Once steps 1–7 are done and verified, you're ready for Phase 1 (Discovery — AS-IS State Document).**
