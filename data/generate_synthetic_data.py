"""
Phase 3 — Synthetic Data Generator
Generates a full synthetic NBA season's worth of fan data across 5 disconnected
"systems" (mirroring the AS-IS state from Phase 1), with realistic data quality
issues baked in on purpose: duplicate fan records, missing linkage keys, nulls,
inconsistent formatting, and orphan references.

Scale: 25,000 total fans, 8,500 of them season ticket holders, 82-game season.
Seeded for reproducibility.
"""
import numpy as np
import pandas as pd
from faker import Faker
import random
import os
from datetime import datetime, timedelta

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

OUT_DIR = os.path.join(os.path.dirname(__file__), "raw")
ANSWER_DIR = os.path.join(os.path.dirname(__file__), "answer_key")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ANSWER_DIR, exist_ok=True)

N_FANS = 25_000
N_STH = 8_500
N_GAMES = 82
SEASON_START = datetime(2025, 10, 21)

print("Generating fans...")

# ---------------------------------------------------------------------------
# 1. FANS (ground-truth master roster — this is the "answer" for fan resolution,
#    not something any real system has in the AS-IS state)
# ---------------------------------------------------------------------------
first_names = [fake.first_name() for _ in range(N_FANS)]
last_names = [fake.last_name() for _ in range(N_FANS)]
true_fan_id = [f"TF{100000+i}" for i in range(N_FANS)]
emails = [f"{fn.lower()}.{ln.lower()}{np.random.randint(1,999)}@{fake.free_email_domain()}" for fn, ln in zip(first_names, last_names)]
phones = [fake.numerify("###-###-####") for _ in range(N_FANS)]
cities = [fake.city() for _ in range(N_FANS)]
states = [fake.state_abbr() for _ in range(N_FANS)]
zips = [fake.zipcode() for _ in range(N_FANS)]
signup_dates = [fake.date_between(start_date="-8y", end_date="-30d") for _ in range(N_FANS)]

is_sth_flag = np.zeros(N_FANS, dtype=bool)
sth_indices = np.random.choice(N_FANS, size=N_STH, replace=False)
is_sth_flag[sth_indices] = True

fans = pd.DataFrame({
    "true_fan_id": true_fan_id,
    "first_name": first_names,
    "last_name": last_names,
    "email": emails,
    "phone": phones,
    "city": cities,
    "state": states,
    "zip": zips,
    "signup_date": signup_dates,
    "is_season_ticket_holder": is_sth_flag,
})

# ---------------------------------------------------------------------------
# 2. GAMES
# ---------------------------------------------------------------------------
print("Generating games...")
opponents = ["Celtics","Knicks","76ers","Bucks","Cavaliers","Bulls","Heat","Nets",
             "Raptors","Hawks","Magic","Hornets","Pistons","Wizards","Pacers",
             "Lakers","Warriors","Nuggets","Suns","Clippers","Kings","Mavericks",
             "Rockets","Grizzlies","Spurs","Thunder","Jazz","Blazers","Timberwolves","Pelicans"]
game_dates = sorted([SEASON_START + timedelta(days=int(d)) for d in np.random.choice(range(0, 175), size=N_GAMES, replace=False)])
opponent_list = np.random.choice(opponents, size=N_GAMES, replace=True)
capacity = 18000
# attendance correlated with day-of-week (weekend games fuller) and opponent popularity
day_of_week = [d.strftime("%A") for d in game_dates]
is_weekend = [dow in ("Friday", "Saturday", "Sunday") for dow in day_of_week]
base_attendance = np.random.normal(loc=15500, scale=1800, size=N_GAMES)
weekend_bump = np.array([900 if w else 0 for w in is_weekend])
attendance = np.clip(base_attendance + weekend_bump, 9000, capacity).astype(int)
is_sellout = attendance >= (capacity * 0.98)

games = pd.DataFrame({
    "game_id": [f"G{2025000+i}" for i in range(N_GAMES)],
    "game_date": game_dates,
    "opponent": opponent_list,
    "day_of_week": day_of_week,
    "is_weekend": is_weekend,
    "final_attendance": attendance,
    "is_sellout": is_sellout,
})

# ---------------------------------------------------------------------------
# 3. SEASON TICKET ACCOUNTS
# ---------------------------------------------------------------------------
print("Generating season ticket accounts...")
sth_fan_ids = fans.loc[fans.is_season_ticket_holder, "true_fan_id"].values
sections = [f"S{n}" for n in range(100, 135)]
tiers = np.random.choice(["Platinum", "Gold", "Silver", "Bronze"], size=N_STH, p=[0.08, 0.22, 0.35, 0.35])
# renewal_status for the season prior to this one (used later as the churn label)
# Higher weight on "renewed" — most STHs renew; the interesting churn signal is the minority who don't
renewal_status = np.random.choice(["renewed", "not_renewed"], size=N_STH, p=[0.91, 0.09])

sth_accounts = pd.DataFrame({
    "sth_account_id": [f"STH{500000+i}" for i in range(N_STH)],
    "true_fan_id": sth_fan_ids,
    "section": np.random.choice(sections, size=N_STH),
    "seat": np.random.randint(1, 22, size=N_STH),
    "membership_tier": tiers,
    "join_year": np.random.randint(2017, 2025, size=N_STH),
    "prior_season_renewal_status": renewal_status,
})

# ---------------------------------------------------------------------------
# 4. TICKETMASTER TRANSACTIONS (siloed system #1 — no export to anywhere else)
#    STHs attend most games at a variable rate; single/multi-game buyers attend a
#    handful. Ticketmaster assigns its OWN customer_id — mostly 1:1 with a fan but
#    ~3% of fans have two ticketmaster_customer_ids (guest checkout vs. logged-in
#    account), which is exactly the kind of identity fragmentation Phase 1 flagged.
# ---------------------------------------------------------------------------
print("Generating ticketmaster transactions (this is the big one)...")

# assign a ticketmaster_customer_id per fan, with ~3% getting a second shadow id
tm_customer_id = {fid: f"TM{700000+i}" for i, fid in enumerate(fans.true_fan_id)}
shadow_fan_ids = np.random.choice(fans.true_fan_id, size=int(N_FANS * 0.03), replace=False)
tm_shadow_id = {fid: f"TM{900000+i}" for i, fid in enumerate(shadow_fan_ids)}

rows = []
purchase_channels = ["web", "mobile_app", "box_office", "phone"]

# STH: attend a variable share of home games, sometimes under the shadow id
for fid in sth_fan_ids:
    attend_rate = np.random.beta(6, 2)  # skewed toward high attendance
    n_attend = int(round(attend_rate * N_GAMES))
    attended_games = np.random.choice(games.game_id, size=min(n_attend, N_GAMES), replace=False)
    cust_id = tm_customer_id[fid]
    for gid in attended_games:
        use_shadow = fid in tm_shadow_id and np.random.rand() < 0.15
        rows.append((
            cust_id if not use_shadow else tm_shadow_id[fid],
            gid,
            np.random.choice(purchase_channels, p=[0.45, 0.4, 0.1, 0.05]),
            round(np.random.normal(95, 30), 2),
        ))

# Single/multi-game buyers: 16,500 fans, most attend 1-3 games total
other_fan_ids = fans.loc[~fans.is_season_ticket_holder, "true_fan_id"].values
n_games_per_fan = np.random.choice([1, 2, 3, 4], size=len(other_fan_ids), p=[0.55, 0.25, 0.13, 0.07])
for fid, n in zip(other_fan_ids, n_games_per_fan):
    attended_games = np.random.choice(games.game_id, size=n, replace=False)
    cust_id = tm_customer_id[fid]
    for gid in attended_games:
        use_shadow = fid in tm_shadow_id and np.random.rand() < 0.15
        rows.append((
            cust_id if not use_shadow else tm_shadow_id[fid],
            gid,
            np.random.choice(purchase_channels, p=[0.5, 0.35, 0.1, 0.05]),
            round(np.random.normal(110, 45), 2),
        ))

ticketmaster = pd.DataFrame(rows, columns=["ticketmaster_customer_id", "game_id", "purchase_channel", "price_paid"])
ticketmaster.insert(0, "transaction_id", [f"TXN{4000000+i}" for i in range(len(ticketmaster))])
ticketmaster["purchase_date"] = ticketmaster["game_id"].map(dict(zip(games.game_id, games.game_date))) - pd.to_timedelta(np.random.randint(1, 90, size=len(ticketmaster)), unit="D")

# --- inject messiness ---
# ~2% missing price_paid
missing_price_idx = np.random.choice(ticketmaster.index, size=int(len(ticketmaster) * 0.02), replace=False)
ticketmaster.loc[missing_price_idx, "price_paid"] = np.nan
# ~0.5% duplicate rows (double-scanned entries)
dup_rows = ticketmaster.sample(frac=0.005, random_state=SEED)
ticketmaster = pd.concat([ticketmaster, dup_rows], ignore_index=True)
# ~0.3% orphan game_id (data entry error referencing a game that doesn't exist)
orphan_idx = np.random.choice(ticketmaster.index, size=int(len(ticketmaster) * 0.003), replace=False)
ticketmaster.loc[orphan_idx, "game_id"] = ticketmaster.loc[orphan_idx, "game_id"].apply(lambda x: f"G{9999}")

print(f"  {len(ticketmaster):,} ticketmaster transactions")

# ---------------------------------------------------------------------------
# 5. ORACLE MICROS CONCESSION TRANSACTIONS (siloed system #2 — loyalty-linked
#    only when a fan scans their card; most gameday concession sales have NO
#    fan linkage at all, mirroring the real POS gap Phase 1 flagged)
# ---------------------------------------------------------------------------
print("Generating concession transactions...")
stands = [f"STAND{n}" for n in range(1, 25)]
items = ["Hot Dog", "Nachos", "Beer", "Soda", "Popcorn", "Pretzel", "Water", "Chicken Tenders", "Pizza Slice"]
item_price = {"Hot Dog": 8.5, "Nachos": 11, "Beer": 12.5, "Soda": 6, "Popcorn": 7.5,
              "Pretzel": 7, "Water": 5, "Chicken Tenders": 13, "Pizza Slice": 9}

micros_rows = []
loyalty_link_rate = 0.35  # only 35% of transactions carry a loyalty/fan-linked ID
for _, game in games.iterrows():
    n_transactions = int(game.final_attendance * np.random.uniform(0.5, 0.7))
    txn_stands = np.random.choice(stands, size=n_transactions)
    txn_items = np.random.choice(items, size=n_transactions)
    has_loyalty = np.random.rand(n_transactions) < loyalty_link_rate
    # loyalty-linked transactions draw from attendees of that game if possible, else any fan
    linked_fan = np.random.choice(fans.true_fan_id, size=n_transactions)
    for i in range(n_transactions):
        price = item_price[txn_items[i]] * np.random.choice([1, 1, 1, 2])  # occasional multi-item order
        micros_rows.append((
            game.game_id,
            txn_stands[i],
            txn_items[i],
            round(price + np.random.normal(0, 0.3), 2),
            linked_fan[i] if has_loyalty[i] else None,
        ))

micros = pd.DataFrame(micros_rows, columns=["game_id", "stand_id", "item", "amount", "loyalty_linked_fan_id"])
micros.insert(0, "transaction_id", [f"MICROS{6000000+i}" for i in range(len(micros))])
game_dt_map = dict(zip(games.game_id, games.game_date))
micros["transaction_datetime"] = micros["game_id"].map(game_dt_map).astype("datetime64[ns]") + pd.to_timedelta(np.random.randint(0, 200, size=len(micros)), unit="m")

# --- inject messiness ---
# ~1% negative amounts (refunds/voids, not flagged as such — realistic mess)
neg_idx = np.random.choice(micros.index, size=int(len(micros) * 0.01), replace=False)
micros.loc[neg_idx, "amount"] = -micros.loc[neg_idx, "amount"].abs()
# the loyalty_linked_fan_id itself uses the TRUE fan id here — but in the real system
# it would actually be the Ticketmaster customer_id OR nothing, never the ground truth.
# Swap linked ids to ticketmaster_customer_id space (where available) to mirror reality,
# and leave the rest null. This is what makes fan resolution in Phase 4/5 a real problem.
micros["loyalty_linked_fan_id"] = micros["loyalty_linked_fan_id"].map(
    lambda fid: tm_customer_id.get(fid) if pd.notna(fid) and np.random.rand() < 0.8 else None
)

print(f"  {len(micros):,} concession transactions")

# ---------------------------------------------------------------------------
# 6. EMAIL / CRM ENGAGEMENT (siloed system #3 — Outlook/Mailchimp equivalent)
# ---------------------------------------------------------------------------
print("Generating email engagement...")
N_CAMPAIGNS = 24
campaign_ids = [f"CAMP{i:03d}" for i in range(N_CAMPAIGNS)]
campaign_dates = sorted(np.random.choice(pd.date_range(SEASON_START - timedelta(days=60), SEASON_START + timedelta(days=170)), size=N_CAMPAIGNS, replace=False))

email_rows = []
# CRM has its own contact records — some fans have duplicate contacts (old + new email)
crm_email_map = dict(zip(fans.true_fan_id, fans.email))
dup_contact_fans = np.random.choice(fans.true_fan_id, size=int(N_FANS * 0.02), replace=False)
crm_dup_email = {fid: fake.free_email() for fid in dup_contact_fans}

for cid, cdate in zip(campaign_ids, campaign_dates):
    # not every fan receives every campaign — sample a subset each time
    recipients = np.random.choice(fans.true_fan_id, size=int(N_FANS * np.random.uniform(0.4, 0.9)), replace=False)
    open_rate = np.random.uniform(0.15, 0.45)
    click_given_open = np.random.uniform(0.1, 0.35)
    opened = np.random.rand(len(recipients)) < open_rate
    clicked = opened & (np.random.rand(len(recipients)) < click_given_open)
    for fid, o, c in zip(recipients, opened, clicked):
        use_dup = fid in crm_dup_email and np.random.rand() < 0.3
        email_rows.append((
            cid, cdate,
            crm_dup_email[fid] if use_dup else crm_email_map[fid],
            bool(o), bool(c),
        ))

email_engagement = pd.DataFrame(email_rows, columns=["campaign_id", "sent_date", "recipient_email", "opened", "clicked"])
email_engagement.insert(0, "engagement_id", [f"EMAIL{8000000+i}" for i in range(len(email_engagement))])

# --- inject messiness ---
# ~4% malformed/inconsistent email casing
mess_idx = np.random.choice(email_engagement.index, size=int(len(email_engagement) * 0.04), replace=False)
email_engagement.loc[mess_idx, "recipient_email"] = email_engagement.loc[mess_idx, "recipient_email"].str.upper()
# ~1% null email (bounced/broken record)
null_idx = np.random.choice(email_engagement.index, size=int(len(email_engagement) * 0.01), replace=False)
email_engagement.loc[null_idx, "recipient_email"] = None

print(f"  {len(email_engagement):,} email engagement records")

# ---------------------------------------------------------------------------
# 7. NPS SURVEYS (siloed system #4 — the Google Sheet)
#    Very sparse: only a small fraction of attendees ever respond, and they
#    self-report an email that frequently doesn't match any other system cleanly.
# ---------------------------------------------------------------------------
print("Generating NPS surveys...")
nps_rows = []
comments_pool = [
    "Great game, but the concession line at my section took forever.",
    "Loved the atmosphere, will be back!",
    "Parking was a nightmare, took 40 min to get out.",
    "Seats were great, staff were friendly.",
    "Wifi didn't work all game.",
    "Best game experience all season.",
    "Bathrooms were dirty by the 3rd quarter.",
    "", "", "",  # many blank comments
]
for _, game in games.iterrows():
    n_responses = int(game.final_attendance * np.random.uniform(0.01, 0.04))  # 1-4% response rate
    for _ in range(n_responses):
        score = np.random.choice(range(0, 11), p=[0.02,0.01,0.02,0.03,0.04,0.06,0.10,0.16,0.22,0.20,0.14])
        self_reported_email = fake.free_email() if np.random.rand() < 0.7 else None  # often blank/anonymous
        nps_rows.append((
            game.game_id,
            self_reported_email,
            score,
            random.choice(comments_pool),
        ))

nps = pd.DataFrame(nps_rows, columns=["game_id", "respondent_email", "score", "comment"])
nps.insert(0, "survey_id", [f"NPS{1000000+i}" for i in range(len(nps))])

print(f"  {len(nps):,} NPS survey responses")

# ---------------------------------------------------------------------------
# 8. FAN DUPLICATE RECORDS (in the fans master extract itself — simulates a
#    fan who re-registered with a slightly different name/email over the years)
# ---------------------------------------------------------------------------
print("Injecting duplicate fan records...")
dup_source_ids = np.random.choice(fans.true_fan_id, size=int(N_FANS * 0.03), replace=False)
dup_rows_fans = fans[fans.true_fan_id.isin(dup_source_ids)].copy()
dup_rows_fans["email"] = dup_rows_fans["email"].apply(lambda e: e.replace("@", "+2@") if np.random.rand() < 0.5 else fake.free_email())
dup_rows_fans["first_name"] = dup_rows_fans["first_name"].apply(lambda n: n.upper() if np.random.rand() < 0.4 else n)
dup_rows_fans["phone"] = None  # duplicate registrations often missing phone

# this is the ground truth mapping we keep OUT of the raw data — it's what Phase 4/5
# fan-resolution logic will need to reconstruct
answer_key = pd.DataFrame({
    "true_fan_id": dup_source_ids,
    "duplicate_of": dup_source_ids,
})

fans_raw = pd.concat([fans, dup_rows_fans], ignore_index=True)
# also null out ~5% of emails and phones across the board (missingness, not duplication)
null_email_idx = np.random.choice(fans_raw.index, size=int(len(fans_raw) * 0.03), replace=False)
fans_raw.loc[null_email_idx, "email"] = None
null_phone_idx = np.random.choice(fans_raw.index, size=int(len(fans_raw) * 0.06), replace=False)
fans_raw.loc[null_phone_idx, "phone"] = None

# ---------------------------------------------------------------------------
# WRITE OUT
# ---------------------------------------------------------------------------
print("Writing CSVs...")
fans_raw.to_csv(os.path.join(OUT_DIR, "fans.csv"), index=False)
games.to_csv(os.path.join(OUT_DIR, "games.csv"), index=False)
sth_accounts.to_csv(os.path.join(OUT_DIR, "season_ticket_accounts.csv"), index=False)
ticketmaster.to_csv(os.path.join(OUT_DIR, "ticketmaster_transactions.csv"), index=False)
micros.to_csv(os.path.join(OUT_DIR, "micros_transactions.csv"), index=False)
email_engagement.to_csv(os.path.join(OUT_DIR, "email_engagement.csv"), index=False)
nps.to_csv(os.path.join(OUT_DIR, "nps_surveys.csv"), index=False)

# answer key + id crosswalks — kept separate, used later to validate fan resolution
answer_key.to_csv(os.path.join(ANSWER_DIR, "duplicate_fan_answer_key.csv"), index=False)
pd.DataFrame([{"true_fan_id": k, "ticketmaster_customer_id": v} for k, v in tm_customer_id.items()]).to_csv(
    os.path.join(ANSWER_DIR, "true_fan_to_ticketmaster_id.csv"), index=False)
pd.DataFrame([{"true_fan_id": k, "ticketmaster_shadow_id": v} for k, v in tm_shadow_id.items()]).to_csv(
    os.path.join(ANSWER_DIR, "ticketmaster_shadow_ids.csv"), index=False)

print("\nDone. Row counts:")
for name, df in [("fans", fans_raw), ("games", games), ("season_ticket_accounts", sth_accounts),
                  ("ticketmaster_transactions", ticketmaster), ("micros_transactions", micros),
                  ("email_engagement", email_engagement), ("nps_surveys", nps)]:
    print(f"  {name}: {len(df):,} rows")
