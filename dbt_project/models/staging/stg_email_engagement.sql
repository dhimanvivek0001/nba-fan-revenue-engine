-- stg_email_engagement: normalizes email casing (fixes the 14,817 ALL-CAPS rows
-- from Phase 3) so joins against stg_fans.email actually match.

select
    engagement_id,
    campaign_id,
    sent_date,
    lower(trim(recipient_email)) as recipient_email,
    opened,
    clicked
from bronze_email_engagement
where recipient_email is not null
