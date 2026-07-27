"""
Phase 7 — Model 3: Customer Lifetime Value (CLV).

Combines a predicted-annual-spend regression with Model 1's churn
probabilities using the standard CLV formula for a non-contractual
relationship with constant retention: CLV = annual_value / churn_rate
(the expected sum of an infinite geometric series of future-year value,
discounted implicitly by the churn probability itself). This directly
reuses Model 1's churn scores rather than re-deriving them, so retention
work (Model 1) and value prioritization (Model 3) stay consistent with
each other — an account's CLV changes if its churn risk changes.
"""
import duckdb
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.metrics import r2_score, mean_absolute_error
import os
import json

SEED = 42
BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DUCKDB_PATH = os.path.join(BASE, "data", "warehouse", "nba_fan_engine.duckdb")
OUT_DIR = os.path.dirname(__file__)
CHURN_SCORES_PATH = os.path.join(BASE, "models", "churn", "churn_scores.csv")

con = duckdb.connect(DUCKDB_PATH)
df = con.execute("""
    select
        s.sth_account_id,
        s.fan_id,
        seg.frequency_games_attended as games_attended,
        seg.monetary_total_spend as total_spend,
        s.membership_tier,
        s.join_year,
        coalesce(eng.emails_received, 0) as emails_received,
        coalesce(eng.emails_opened, 0) as emails_opened
    from main_staging.stg_season_ticket_accounts s
    join main_marts.fan_rfm_segments seg on s.fan_id = seg.fan_id
    left join (
        select fan_id, count(*) as emails_received, sum(case when opened then 1 else 0 end) as emails_opened
        from main_marts.fact_engagement
        where fan_id is not null
        group by 1
    ) eng on s.fan_id = eng.fan_id
""").fetchdf()
con.close()

N_GAMES = 82
CURRENT_YEAR = 2026
df["attendance_rate"] = df["games_attended"] / N_GAMES
df["tenure_years"] = CURRENT_YEAR - df["join_year"]
df["email_open_rate"] = np.where(df["emails_received"] > 0, df["emails_opened"] / df["emails_received"], np.nan)

# --- Step 1: predict this-season spend from tenure/attendance/tier/engagement ---
feature_cols = ["attendance_rate", "tenure_years", "email_open_rate", "emails_received"]
X = pd.get_dummies(df[feature_cols + ["membership_tier"]], columns=["membership_tier"])
y = df["total_spend"]

model = Ridge(alpha=1.0, random_state=SEED)
kf = KFold(n_splits=5, shuffle=True, random_state=SEED)
X_filled = X.fillna(X.median())
cv_preds = cross_val_predict(model, X_filled, y, cv=kf)
r2 = r2_score(y, cv_preds)
mae = mean_absolute_error(y, cv_preds)
print(f"Annual spend model — 5-fold CV R²: {r2:.3f}, MAE: ${mae:,.0f}")

model.fit(X_filled, y)
df["predicted_annual_spend"] = model.predict(X_filled).clip(min=0)

# --- Step 2: bring in Model 1's churn probabilities ---
churn_scores = pd.read_csv(CHURN_SCORES_PATH)[["sth_account_id", "churn_risk_score"]]
df = df.merge(churn_scores, on="sth_account_id", how="left")
df["churn_probability"] = (df["churn_risk_score"] / 100).clip(lower=0.02, upper=0.95)  # floor/cap avoids division blowups

# --- Step 3: CLV = annual value / churn rate, capped at a sane horizon ---
MAX_HORIZON_YEARS = 12  # cap: even a near-zero churn account isn't modeled as "worth infinity"
df["implied_lifetime_years"] = (1 / df["churn_probability"]).clip(upper=MAX_HORIZON_YEARS)
df["clv"] = (df["predicted_annual_spend"] * df["implied_lifetime_years"]).round(0)

# --- Outputs ---
df_out = df[[
    "sth_account_id", "fan_id", "membership_tier", "tenure_years",
    "predicted_annual_spend", "churn_probability", "implied_lifetime_years", "clv"
]].sort_values("clv", ascending=False)
df_out.to_csv(os.path.join(OUT_DIR, "clv_scores.csv"), index=False)

total_clv = df_out["clv"].sum()
avg_clv = df_out["clv"].mean()
print(f"\nTotal portfolio CLV across {len(df_out):,} STH accounts: ${total_clv:,.0f}")
print(f"Average CLV per account: ${avg_clv:,.0f}")

metrics = {
    "spend_model_cv_r2": round(float(r2), 3),
    "spend_model_mae": round(float(mae), 0),
    "n_accounts": int(len(df_out)),
    "total_portfolio_clv": round(float(total_clv), 0),
    "avg_clv": round(float(avg_clv), 0),
    "max_horizon_years_cap": MAX_HORIZON_YEARS,
}
with open(os.path.join(OUT_DIR, "clv_model_metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2)

print("\nTop 10 highest-CLV accounts:")
print(df_out.head(10).to_string(index=False))
print("\nCLV by membership tier:")
print(df.groupby("membership_tier")["clv"].agg(["mean", "count"]).round(0))
