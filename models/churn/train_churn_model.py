"""
Phase 7 — Model 1: Season Ticket Holder Churn Prediction.

Fulfills BRD FR-03 (churn risk score 0-100 for every active STH, AUC >= 0.75),
FR-04 (human-readable reason code per flagged account via SHAP), and FR-05
(quantify total at-risk revenue in dollars).
"""
import duckdb
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report
import xgboost as xgb
import shap
import os
import json

SEED = 42
BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # project root
DUCKDB_PATH = os.path.join(BASE, "data", "warehouse", "nba_fan_engine.duckdb")
OUT_DIR = os.path.dirname(__file__)  # models/churn/

con = duckdb.connect(DUCKDB_PATH)

df = con.execute("""
    select
        s.sth_account_id,
        s.fan_id,
        seg.frequency_games_attended as games_attended,
        seg.monetary_total_spend as total_spend,
        coalesce(seg.recency_days_since_last_game, 999) as recency_days,
        s.membership_tier,
        s.join_year,
        coalesce(eng.emails_received, 0) as emails_received,
        coalesce(eng.emails_opened, 0) as emails_opened,
        s.prior_season_renewal_status
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

print(f"Loaded {len(df):,} STH accounts")

# --- Feature engineering ---
N_GAMES = 82
CURRENT_YEAR = 2026
df["attendance_rate"] = df["games_attended"] / N_GAMES
df["email_open_rate"] = np.where(df["emails_received"] > 0, df["emails_opened"] / df["emails_received"], np.nan)
df["tenure_years"] = CURRENT_YEAR - df["join_year"]
df["avg_spend_per_game"] = np.where(df["games_attended"] > 0, df["total_spend"] / df["games_attended"], 0)

df["target_churn"] = (df["prior_season_renewal_status"] == "not_renewed").astype(int)

feature_cols = [
    "attendance_rate", "total_spend", "recency_days", "tenure_years",
    "email_open_rate", "emails_received", "avg_spend_per_game",
]
categorical_cols = ["membership_tier"]

X = pd.get_dummies(df[feature_cols + categorical_cols], columns=categorical_cols, dummy_na=False)
y = df["target_churn"]

X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
    X, y, df.index, test_size=0.25, random_state=SEED, stratify=y
)

model = xgb.XGBClassifier(
    n_estimators=200, max_depth=4, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, eval_metric="auc",
    random_state=SEED, missing=np.nan,
)
model.fit(X_train, y_train)

y_pred_proba = model.predict_proba(X_test)[:, 1]
auc = roc_auc_score(y_test, y_pred_proba)
print(f"\nTest AUC: {auc:.4f}  (BRD FR-03 target: >= 0.75)")
print("\nClassification report (threshold 0.5):")
print(classification_report(y_test, (y_pred_proba >= 0.5).astype(int)))

# --- Score every STH account (not just test set) ---
all_proba = model.predict_proba(X)[:, 1]
df["churn_risk_score"] = (all_proba * 100).round(1)

# --- SHAP values for reason codes (FR-04) ---
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)

feature_names = X.columns.tolist()

def top_reason_codes(row_idx, n=2):
    contribs = shap_values[row_idx]
    # only positive contributions (pushing toward churn) are relevant reason codes
    positive_idx = np.argsort(contribs)[::-1][:n]
    reasons = []
    for i in positive_idx:
        if contribs[i] > 0.01:
            fname = feature_names[i]
            reasons.append(fname)
    return reasons

readable_names = {
    "attendance_rate": "low game attendance",
    "total_spend": "low total spend",
    "recency_days": "long gap since last game attended",
    "tenure_years": "tenure",
    "email_open_rate": "low email engagement",
    "emails_received": "few emails received",
    "avg_spend_per_game": "low spend per game",
}

reason_lists = []
for i in range(len(df)):
    raw_reasons = top_reason_codes(i)
    readable = [readable_names.get(r, r) for r in raw_reasons if not r.startswith("membership_tier")]
    reason_lists.append(readable if readable else ["no dominant single factor"])

df["reason_codes"] = [", ".join(r) for r in reason_lists]

# --- Business impact: $ at risk (FR-05) ---
RISK_THRESHOLD = 60  # score >= 60 treated as "at risk" for outreach prioritization
at_risk = df[df["churn_risk_score"] >= RISK_THRESHOLD]
avg_account_value = df["total_spend"].mean()
total_at_risk_dollars = at_risk["total_spend"].sum()

print(f"\n--- Business Impact (FR-05) ---")
print(f"Accounts scored >= {RISK_THRESHOLD} risk: {len(at_risk):,} of {len(df):,} ({100*len(at_risk)/len(df):.1f}%)")
print(f"Total at-risk revenue (sum of their spend): ${total_at_risk_dollars:,.0f}")
print(f"(Phase 1 baseline estimate was $2.4M)")

# --- Save outputs ---
df[["sth_account_id", "fan_id", "churn_risk_score", "reason_codes", "prior_season_renewal_status"]].to_csv(
    os.path.join(OUT_DIR, "churn_scores.csv"), index=False
)

model.save_model(os.path.join(OUT_DIR, "churn_model.json"))

metrics = {
    "test_auc": round(float(auc), 4),
    "n_accounts_scored": int(len(df)),
    "n_at_risk_threshold_60": int(len(at_risk)),
    "total_at_risk_dollars": round(float(total_at_risk_dollars), 0),
    "feature_importance": dict(sorted(
        zip(feature_names, model.feature_importances_.tolist()),
        key=lambda x: -x[1]
    )),
}
with open(os.path.join(OUT_DIR, "churn_model_metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2)

print(f"\nSaved: churn_scores.csv, churn_model.json, churn_model_metrics.json")
print("\nTop 10 highest-risk accounts:")
print(df.nlargest(10, "churn_risk_score")[["sth_account_id", "churn_risk_score", "reason_codes", "total_spend"]].to_string(index=False))
