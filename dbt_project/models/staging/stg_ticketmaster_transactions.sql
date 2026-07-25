-- stg_ticketmaster_transactions: applies the 3 fixes the Phase 3 DQ report called for:
--   1. drop exact duplicate transactions (double-scans) — 2,743 rows in Bronze
--   2. quarantine orphan game_id references (don't silently join-fail downstream) — 1,662 rows
--   3. flag (don't drop) null price_paid so revenue models can choose how to handle it

with deduped as (

    -- collapse on transaction_id itself (a repeated transaction_id is, by
    -- definition, the same logged event twice — even if a downstream data
    -- error like an orphan game_id correction only touched one of the two
    -- copies). Prefer the copy with a valid game reference and a non-null price.
    select
        transaction_id,
        ticketmaster_customer_id,
        game_id,
        purchase_channel,
        price_paid,
        purchase_date
    from bronze_ticketmaster_transactions
    qualify row_number() over (
        partition by transaction_id
        order by (price_paid is not null) desc, game_id
    ) = 1

)

select
    d.transaction_id,
    d.ticketmaster_customer_id,
    d.game_id,
    d.purchase_channel,
    d.price_paid,
    (d.price_paid is null) as is_price_missing,
    d.purchase_date,
    (g.game_id is null) as is_orphan_game_reference
from deduped d
left join bronze_games g on d.game_id = g.game_id
