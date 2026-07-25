-- fact_concessions: grain is one row per concession transaction. fan_id resolved
-- where a loyalty-linked ticketmaster_customer_id exists (28% of rows, per the
-- Phase 3 DQ finding) — the remaining 72% are legitimately fan-anonymous and
-- feed game/stand-level forecasting (Phase 7) rather than fan-level features.

select
    c.transaction_id,
    c.game_id,
    c.stand_id,
    c.item,
    c.amount,
    c.is_refund_or_void,
    c.transaction_datetime,
    m.fan_id
from {{ ref('stg_micros_transactions') }} c
left join {{ ref('int_fan_identity_map') }} m
    on c.loyalty_linked_ticketmaster_customer_id = m.ticketmaster_customer_id
