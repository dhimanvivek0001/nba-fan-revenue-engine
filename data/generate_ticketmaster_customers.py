"""
Phase 4 addendum — Ticketmaster Customer Dimension.

Phase 3 generated ticketmaster_transactions with only a ticketmaster_customer_id
(no name/email), which would make fan identity resolution literally impossible —
real ticketing systems always capture a name and email at checkout, even when
they don't share a customer ID with any other system. This script adds that
missing (but realistic) piece: a ticketmaster_customers dimension, keyed by
ticketmaster_customer_id, carrying the name/email captured at checkout — with
its own realistic messiness (casing, occasional nicknames).

This is the table Phase 4's identity-resolution model joins against stg_fans.
"""
import pandas as pd
import numpy as np
from faker import Faker
import os

SEED = 42
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

BASE = os.path.dirname(__file__)
RAW = os.path.join(BASE, "raw")
ANSWER = os.path.join(BASE, "answer_key")

fans = pd.read_csv(os.path.join(RAW, "fans.csv"))
# use only the canonical (non-duplicate) fan rows as the source of truth for name/email
fans = fans.drop_duplicates(subset="true_fan_id", keep="first")

primary_map = pd.read_csv(os.path.join(ANSWER, "true_fan_to_ticketmaster_id.csv"))
shadow_map = pd.read_csv(os.path.join(ANSWER, "ticketmaster_shadow_ids.csv"))

fan_lookup = fans.set_index("true_fan_id")[["first_name", "last_name", "email"]]

def build_customer_rows(id_map, id_col, is_shadow=False):
    rows = []
    for _, r in id_map.iterrows():
        fid = r["true_fan_id"]
        if fid not in fan_lookup.index:
            continue
        fname, lname, email = fan_lookup.loc[fid, ["first_name", "last_name", "email"]]
        full_name = f"{fname} {lname}"
        # realistic messiness: ~15% of records have inconsistent name casing
        if np.random.rand() < 0.15:
            full_name = full_name.upper() if np.random.rand() < 0.5 else full_name.lower()
        # shadow (guest checkout) accounts: same email reused, but ~10% use a slightly
        # different email (e.g. a second personal address) — the harder resolution case
        cust_email = email
        if is_shadow and np.random.rand() < 0.10 and pd.notna(email):
            cust_email = email.split("@")[0] + "+guest@" + email.split("@")[1]
        rows.append((r[id_col], full_name, cust_email))
    return rows

rows = build_customer_rows(primary_map, "ticketmaster_customer_id", is_shadow=False)
rows += build_customer_rows(shadow_map, "ticketmaster_shadow_id", is_shadow=True)

customers = pd.DataFrame(rows, columns=["ticketmaster_customer_id", "full_name", "email"])

# a small share of emails never captured (phone/box-office purchase, no email on file)
null_idx = customers.sample(frac=0.04, random_state=SEED).index
customers.loc[null_idx, "email"] = None

customers.to_csv(os.path.join(RAW, "ticketmaster_customers.csv"), index=False)
print(f"ticketmaster_customers.csv written: {len(customers):,} rows")
print(customers.head(8).to_string())
