select
    observed_at,
    station_id,
    bike_count
from {{ source('raw', 'raw_mobility_counts') }}

