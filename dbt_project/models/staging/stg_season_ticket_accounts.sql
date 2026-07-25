select
    sth_account_id,
    true_fan_id as fan_id,
    section,
    seat,
    membership_tier,
    join_year,
    prior_season_renewal_status
from bronze_season_ticket_accounts
