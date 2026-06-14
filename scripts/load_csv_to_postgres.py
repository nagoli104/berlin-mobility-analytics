#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg2


RAW_MOBILITY_COUNTS_TABLE = "raw_mobility_counts"
RAW_STATION_METADATA_TABLE = "raw_station_metadata"
RAW_WEATHER_HOURLY_TABLE = "raw_weather_hourly"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load extracted Berlin mobility CSV files into Postgres raw tables."
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("MOBILITY_DATABASE_URL"),
        help="Postgres connection URL. Defaults to MOBILITY_DATABASE_URL.",
    )
    parser.add_argument(
        "--counts",
        type=Path,
        required=True,
        help="Path to mobility_long.csv.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        required=True,
        help="Path to mobility_metadata.csv.",
    )
    parser.add_argument(
        "--weather",
        type=Path,
        help="Optional path to hourly weather CSV.",
    )
    parser.add_argument(
        "--if-exists",
        choices=["replace", "append"],
        default="replace",
        help="Whether to truncate raw tables before loading.",
    )
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or MOBILITY_DATABASE_URL is required")

    return args


def require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"CSV file does not exist: {path}")


def create_tables(cursor) -> None:
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {RAW_MOBILITY_COUNTS_TABLE} (
            observed_at TIMESTAMPTZ NOT NULL,
            station_id TEXT NOT NULL,
            bike_count DOUBLE PRECISION NOT NULL
        );
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {RAW_STATION_METADATA_TABLE} (
            station_id TEXT NOT NULL,
            description TEXT,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            installed DATE,
            direction TEXT
        );
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {RAW_WEATHER_HOURLY_TABLE} (
            date TIMESTAMPTZ NOT NULL,
            temperature_2m DOUBLE PRECISION,
            apparent_temperature DOUBLE PRECISION,
            precipitation DOUBLE PRECISION,
            weather_code INTEGER,
            cloud_cover DOUBLE PRECISION,
            wind_speed_10m DOUBLE PRECISION,
            relative_humidity_2m DOUBLE PRECISION,
            wind_gusts_10m DOUBLE PRECISION,
            weather_description TEXT
        );
        """
    )


def truncate_tables(cursor, include_weather: bool) -> None:
    tables = [
        RAW_MOBILITY_COUNTS_TABLE,
        RAW_STATION_METADATA_TABLE,
    ]
    if include_weather:
        tables.append(RAW_WEATHER_HOURLY_TABLE)

    cursor.execute(f"TRUNCATE TABLE {', '.join(tables)};")


def copy_csv(cursor, table_name: str, csv_path: Path) -> None:
    with csv_path.open("r", encoding="utf-8", newline="") as file:
        cursor.copy_expert(
            f"COPY {table_name} FROM STDIN WITH (FORMAT CSV, HEADER TRUE)",
            file,
        )


def count_rows(cursor, table_name: str) -> int:
    cursor.execute(f"SELECT count(*) FROM {table_name};")
    return cursor.fetchone()[0]


def main() -> None:
    args = parse_args()

    require_file(args.counts)
    require_file(args.metadata)
    if args.weather is not None:
        require_file(args.weather)

    with psycopg2.connect(args.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TIME ZONE 'Europe/Berlin';")
            create_tables(cursor)

            if args.if_exists == "replace":
                truncate_tables(cursor, include_weather=args.weather is not None)

            copy_csv(cursor, RAW_MOBILITY_COUNTS_TABLE, args.counts)
            copy_csv(cursor, RAW_STATION_METADATA_TABLE, args.metadata)

            if args.weather is not None:
                copy_csv(cursor, RAW_WEATHER_HOURLY_TABLE, args.weather)

            loaded_tables = [
                RAW_MOBILITY_COUNTS_TABLE,
                RAW_STATION_METADATA_TABLE,
            ]
            if args.weather is not None:
                loaded_tables.append(RAW_WEATHER_HOURLY_TABLE)

            for table_name in loaded_tables:
                print(f"{table_name}: {count_rows(cursor, table_name):,} rows")


if __name__ == "__main__":
    main()
