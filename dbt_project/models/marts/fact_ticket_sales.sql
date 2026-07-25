-- fact_ticket_sales: grain is one row per ticket transaction. fan_id resolved
-- via int_fan_identity_map (the Phase 4 identity resolution model), so every
-- ticket purchase — regardless of which Ticketmaster customer_id it was logged
-- under — rolls up to a single canonical fan.

select
    t.transaction_id,
    m.fan_id,
    t.game_id,
    t.purchase_channel,
    t.price_paid,
    t.is_price_missing,
    t.purchase_date,
    t.is_orphan_game_reference
from {{ ref('stg_ticketmaster_transactions') }} t
left join {{ ref('int_fan_identity_map') }} m
    on t.ticketmaster_customer_id = m.ticketmaster_customer_id
where not t.is_orphan_game_reference  -- orphan rows can't join to a real game; excluded from analysis-ready fact
