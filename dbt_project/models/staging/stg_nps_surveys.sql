-- stg_nps_surveys: normalizes respondent email where present. Note 29.9% of rows
-- have no respondent email at all (Phase 3 finding) — those remain usable for
-- aggregate/game-level sentiment but can't be attributed to a fan.

select
    survey_id,
    game_id,
    lower(trim(respondent_email)) as respondent_email,
    score,
    comment,
    (respondent_email is null) as is_anonymous
from bronze_nps_surveys
