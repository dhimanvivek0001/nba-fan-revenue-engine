"""
Loads every raw CSV in data/raw/ into the local DuckDB warehouse as a
bronze_<table> table. Run this after generate_synthetic_data.py and
generate_ticketmaster_customers.py, and before `dbt run`.
"""
import duckdb
import os

BASE = os.path.dirname(__file__)
RAW_DIR = os.path.join(BASE, "raw")
WAREHOUSE_DIR = os.path.join(BASE, "warehouse")
os.makedirs(WAREHOUSE_DIR, exist_ok=True)
DUCKDB_PATH = os.path.join(WAREHOUSE_DIR, "nba_fan_engine.duckdb")

TABLES = [
    "fans", "games", "season_ticket_accounts", "ticketmaster_transactions",
    "ticketmaster_customers", "micros_transactions", "email_engagement", "nps_surveys",
]

con = duckdb.connect(DUCKDB_PATH)
for t in TABLES:
    csv_path = os.path.join(RAW_DIR, f"{t}.csv")
    con.execute(f"CREATE OR REPLACE TABLE bronze_{t} AS SELECT * FROM read_csv_auto('{csv_path}')")
    cnt = con.execute(f"SELECT COUNT(*) FROM bronze_{t}").fetchone()[0]
    print(f"Loaded bronze_{t}: {cnt:,} rows")
con.close()
print("\nBronze layer loaded successfully.")
