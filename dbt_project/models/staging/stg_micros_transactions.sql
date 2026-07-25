-- stg_micros_transactions: flags refund/void-like negative amounts (1.0% of Bronze
-- rows) instead of silently including them in average-transaction-value math, and
-- carries the loyalty-linked ticketmaster_customer_id through unchanged (72.0% of
-- rows have none — that gap is real and is not something staging can fix; see the
-- Phase 3 DQ Findings Report).

select
    transaction_id,
    game_id,
    stand_id,
    item,
    amount,
    (amount < 0) as is_refund_or_void,
    loyalty_linked_fan_id as loyalty_linked_ticketmaster_customer_id,
    transaction_datetime
from bronze_micros_transactions
