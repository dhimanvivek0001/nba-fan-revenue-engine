select
    game_id,
    game_date,
    opponent,
    day_of_week,
    is_weekend,
    final_attendance,
    is_sellout,
    extract(month from game_date) as game_month,
    extract(year from game_date) as game_year
from {{ ref('stg_games') }}
