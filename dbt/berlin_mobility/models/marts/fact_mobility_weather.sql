with mobility_counts as (
    select
        observed_at,
        station_id,
        bike_count
    from {{ ref('stg_mobility_counts') }}
),

station_metadata as (
    select
        station_id,
        description as station_description,
        latitude as station_latitude,
        longitude as station_longitude,
        installed as station_installed_date,
        direction as station_direction
    from {{ ref('stg_station_metadata') }}
),

weather_hourly as (
    select
        weather_at,
        temperature_2m,
        apparent_temperature,
        precipitation,
        weather_code,
        cloud_cover,
        wind_speed_10m,
        relative_humidity_2m,
        wind_gusts_10m,
        weather_description
    from {{ ref('stg_weather_hourly') }}
)

select
    mobility_counts.observed_at,
    timezone('Europe/Berlin', mobility_counts.observed_at) as observed_local_at,
    mobility_counts.station_id,
    mobility_counts.bike_count,

    cast(timezone('Europe/Berlin', mobility_counts.observed_at) as date) as observed_date,
    extract(hour from timezone('Europe/Berlin', mobility_counts.observed_at))::integer as observed_hour,
    extract(isodow from timezone('Europe/Berlin', mobility_counts.observed_at))::integer as observed_isodow,
    extract(isodow from timezone('Europe/Berlin', mobility_counts.observed_at))::integer in (6, 7) as is_weekend,

    station_metadata.station_description,
    station_metadata.station_latitude,
    station_metadata.station_longitude,
    station_metadata.station_installed_date,
    station_metadata.station_direction,

    weather_hourly.temperature_2m,
    weather_hourly.apparent_temperature,
    weather_hourly.precipitation,
    weather_hourly.weather_code,
    weather_hourly.cloud_cover,
    weather_hourly.wind_speed_10m,
    weather_hourly.relative_humidity_2m,
    weather_hourly.wind_gusts_10m,
    weather_hourly.weather_description
from mobility_counts
left join station_metadata
    on mobility_counts.station_id = station_metadata.station_id
left join weather_hourly
    on mobility_counts.observed_at = weather_hourly.weather_at
