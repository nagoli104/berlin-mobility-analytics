select
    date as weather_at,
    temperature_2m,
    apparent_temperature,
    precipitation,
    weather_code,
    cloud_cover,
    wind_speed_10m,
    relative_humidity_2m,
    wind_gusts_10m,
    weather_description
from {{ source('raw', 'raw_weather_hourly') }}

