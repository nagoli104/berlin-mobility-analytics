#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry


DEFAULT_HOURLY_VARIABLES = [
    "temperature_2m",
    "apparent_temperature",
    "precipitation",
    "weather_code",
    "cloud_cover",
    "wind_speed_10m",
    "relative_humidity_2m",
    "wind_gusts_10m",
]

WEATHER_CODE_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download historical hourly weather data from Open-Meteo."
    )
    parser.add_argument("--latitude", type=float, required=True, help="Latitude")
    parser.add_argument("--longitude", type=float, required=True, help="Longitude")
    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Start date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="End date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output CSV path",
    )
    parser.add_argument(
        "--timezone",
        type=str,
        default="Europe/Berlin",
        help='Output timezone, e.g. "Europe/Berlin"',
    )
    parser.add_argument(
        "--cache-path",
        type=str,
        default=".cache",
        help="Path for HTTP cache",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=5,
        help="Number of retries for failed requests",
    )
    parser.add_argument(
        "--backoff-factor",
        type=float,
        default=0.2,
        help="Retry backoff factor",
    )
    parser.add_argument(
        "--hourly",
        nargs="+",
        default=DEFAULT_HOURLY_VARIABLES,
        help="Hourly variables to request",
    )
    return parser.parse_args()


def build_client(
    cache_path: str,
    retries: int,
    backoff_factor: float,
) -> openmeteo_requests.Client:
    cache_session = requests_cache.CachedSession(cache_path, expire_after=-1)
    retry_session = retry(
        cache_session,
        retries=retries,
        backoff_factor=backoff_factor,
    )
    return openmeteo_requests.Client(session=retry_session)


def fetch_weather_data(
    client: openmeteo_requests.Client,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    hourly_variables: list[str],
):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": hourly_variables,
    }

    responses = client.weather_api(url, params=params)
    if not responses:
        raise RuntimeError("No response returned from Open-Meteo API.")

    return responses[0]


def response_to_dataframe(
    response,
    hourly_variables: list[str],
    timezone: str = "Europe/Berlin",
) -> pd.DataFrame:
    hourly = response.Hourly()

    start_time = pd.to_datetime(hourly.Time(), unit="s", utc=True)
    end_time = pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True)
    interval = pd.Timedelta(seconds=hourly.Interval())

    timestamps = pd.date_range(
        start=start_time,
        end=end_time,
        freq=interval,
        inclusive="left",
    ).tz_convert(timezone)

    data = {"date": timestamps}

    for idx, variable_name in enumerate(hourly_variables):
        data[variable_name] = hourly.Variables(idx).ValuesAsNumpy()

    df = pd.DataFrame(data)

    if "weather_code" in df.columns:
        # cast to nullable integer first so mapping is robust
        df["weather_code"] = pd.Series(df["weather_code"]).round().astype("Int64")
        df["weather_description"] = df["weather_code"].map(WEATHER_CODE_DESCRIPTIONS)

    return df


def main() -> None:
    args = parse_args()

    client = build_client(
        cache_path=args.cache_path,
        retries=args.retries,
        backoff_factor=args.backoff_factor,
    )

    response = fetch_weather_data(
        client=client,
        latitude=args.latitude,
        longitude=args.longitude,
        start_date=args.start_date,
        end_date=args.end_date,
        hourly_variables=args.hourly,
    )

    print(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
    print(f"Elevation: {response.Elevation()} m asl")
    print(f"Timezone difference to GMT+0 from API: {response.UtcOffsetSeconds()} s")

    hourly_df = response_to_dataframe(
        response=response,
        hourly_variables=args.hourly,
        timezone=args.timezone,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    hourly_df.to_csv(args.output, index=False)

    print(f"Saved {len(hourly_df):,} rows to {args.output}")
    print(f"Timestamps converted to timezone: {args.timezone}")


if __name__ == "__main__":
    main()