"""
Phase 7 — Model 4: Concessions Demand Forecasting.

Fulfills BRD FR-08 (forecast concession demand by stand and gameday, MAPE <=
20% on held-out games). Grain is game x stand, not fan-level — Phase 3/5
established that 72% of concession transactions carry no fan linkage at all,
so fan-level forecasting isn't possible with this data; game/stand level is
the right (and only supportable) grain for gameday staffing decisions anyway.

Validation uses GroupKFold by game_id rather than a random row split — a
random split would let transactions from the same game leak across train/test,
which would make the held-out MAPE meaningless for this use case (the real
question is "can we forecast a game we haven't seen yet").
"""
import duckdb
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GroupKFold, cross_val_predict
import os
import json

SEED = 42
BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DUCKDB_PATH = os.path.join(BASE, "data", "warehouse", "nba_fan_engine.duckdb")
OUT_DIR = os.path.dirname(__file__)

con = duckdb.connect(DUCKDB_PATH)
agg = con.execute("""
    select
        c.game_id,
        c.stand_id,
        count(*) as transaction_count,
        round(sum(c.amount), 2) as total_revenue
    from main_marts.fact_concessions c
    where not c.is_refund_or_void
    group by 1, 2
""").fetchdf()

games = con.execute("""
    select game_id, final_attendance, is_weekend, day_of_week, game_month
    from main_marts.dim_game
""").fetchdf()
con.close()

df = agg.merge(games, on="game_id", how="left")
print(f"Dataset: {len(df):,} game x stand rows across {df['game_id'].nunique()} games and {df['stand_id'].nunique()} stands")

# --- Features ---
feature_cols = ["final_attendance", "is_weekend", "game_month"]
X = pd.get_dummies(df[feature_cols + ["stand_id", "day_of_week"]], columns=["stand_id", "day_of_week"])
y = df["transaction_count"]

model = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=SEED)

# GroupKFold by game_id: an entire game's rows stay together in either train
# or test, so the model is validated on games it has genuinely never seen
gkf = GroupKFold(n_splits=5)
cv_preds = cross_val_predict(model, X, y, cv=gkf, groups=df["game_id"])

df["predicted_transaction_count"] = cv_preds
df["abs_pct_error"] = (np.abs(df["transaction_count"] - df["predicted_transaction_count"]) / df["transaction_count"]).replace([np.inf, -np.inf], np.nan)
mape = df["abs_pct_error"].dropna().mean() * 100

print(f"\nConcessions demand model — GroupKFold (by game) MAPE: {mape:.1f}%  (BRD FR-08 target: <= 20%)")

# fit final model on all data for feature importance + forward-looking use
model.fit(X, y)
importances = dict(sorted(zip(X.columns, model.feature_importances_.tolist()), key=lambda x: -x[1])[:10])

# --- Output: per game x stand forecast table ---
df_out = df[["game_id", "stand_id", "final_attendance", "transaction_count", "predicted_transaction_count", "abs_pct_error"]].copy()
df_out["predicted_transaction_count"] = df_out["predicted_transaction_count"].round(1)
df_out.to_csv(os.path.join(OUT_DIR, "concessions_forecast.csv"), index=False)

# --- Staffing implication: rank stands by predicted volume per game (for gameday ops) ---
staffing_priority = df.groupby(["game_id", "stand_id"])["predicted_transaction_count"].mean().reset_index()
staffing_priority = staffing_priority.sort_values(["game_id", "predicted_transaction_count"], ascending=[True, False])
staffing_priority.to_csv(os.path.join(OUT_DIR, "staffing_priority_by_game.csv"), index=False)

metrics = {
    "mape_pct": round(float(mape), 1),
    "n_games": int(df["game_id"].nunique()),
    "n_stands": int(df["stand_id"].nunique()),
    "n_game_stand_rows": int(len(df)),
    "top_feature_importances": importances,
}
with open(os.path.join(OUT_DIR, "concessions_model_metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2)

print(f"\nTop feature importances:")
for k, v in importances.items():
    print(f"  {k}: {v:.3f}")

print("\nSample: predicted vs actual for one game (first game_id in the data):")
sample_game = df["game_id"].iloc[0]
print(df[df.game_id == sample_game][["stand_id", "final_attendance", "transaction_count", "predicted_transaction_count"]].sort_values("transaction_count", ascending=False).to_string(index=False))
