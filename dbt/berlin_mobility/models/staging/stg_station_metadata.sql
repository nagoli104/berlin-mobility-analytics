select
    station_id,
    description,
    latitude,
    longitude,
    installed,
    direction
from {{ source('raw', 'raw_station_metadata') }}

