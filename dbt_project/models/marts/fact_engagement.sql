-- fact_engagement: grain is one row per email sent. fan_id joined directly on
-- normalized email (the CRM captures the fan's true email, so no identity-map
-- hop is needed here — unlike Ticketmaster/MICROS which use their own IDs).
--
-- Note: at 25,000-fan scale, a handful of fans (4 pairs) coincidentally share
-- an identical generated email. Deduped deterministically (lowest fan_id wins)
-- so the join can't fan out — the same defensive pattern used in
-- int_fan_identity_map for Ticketmaster's name-collision case.

with fan_by_email as (
    select fan_id, email
    from {{ ref('stg_fans') }}
    where email is not null
    qualify row_number() over (partition by email order by fan_id) = 1
)

select
    e.engagement_id,
    f.fan_id,
    e.campaign_id,
    e.sent_date,
    e.opened,
    e.clicked
from {{ ref('stg_email_engagement') }} e
left join fan_by_email f
    on e.recipient_email = f.email
