#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

import psycopg2


@dataclass(frozen=True)
class Check:
    name: str
    sql: str


CHECKS = [
    Check(
        name="raw_mobility_counts has rows",
        sql="SELECT CASE WHEN count(*) = 0 THEN 1 ELSE 0 END FROM raw_mobility_counts;",
    ),
    Check(
        name="raw_mobility_counts observed_at is not null",
        sql="SELECT count(*) FROM raw_mobility_counts WHERE observed_at IS NULL;",
    ),
    Check(
        name="raw_mobility_counts station_id is not null",
        sql="SELECT count(*) FROM raw_mobility_counts WHERE station_id IS NULL;",
    ),
    Check(
        name="raw_mobility_counts bike_count is not negative",
        sql="SELECT count(*) FROM raw_mobility_counts WHERE bike_count < 0;",
    ),
    Check(
        name="raw_mobility_counts station-hour key is unique",
        sql="""
        SELECT count(*)
        FROM (
            SELECT observed_at, station_id
            FROM raw_mobility_counts
            GROUP BY observed_at, station_id
            HAVING count(*) > 1
        ) duplicates;
        """,
    ),
    Check(
        name="raw_station_metadata has rows",
        sql="SELECT CASE WHEN count(*) = 0 THEN 1 ELSE 0 END FROM raw_station_metadata;",
    ),
    Check(
        name="raw_station_metadata station_id is not null",
        sql="SELECT count(*) FROM raw_station_metadata WHERE station_id IS NULL;",
    ),
    Check(
        name="raw_station_metadata station_id is unique",
        sql="""
        SELECT count(*)
        FROM (
            SELECT station_id
            FROM raw_station_metadata
            GROUP BY station_id
            HAVING count(*) > 1
        ) duplicates;
        """,
    ),
    Check(
        name="raw_station_metadata coordinates are in plausible ranges",
        sql="""
        SELECT count(*)
        FROM raw_station_metadata
        WHERE latitude NOT BETWEEN -90 AND 90
           OR longitude NOT BETWEEN -180 AND 180;
        """,
    ),
    Check(
        name="raw_weather_hourly has rows",
        sql="SELECT CASE WHEN count(*) = 0 THEN 1 ELSE 0 END FROM raw_weather_hourly;",
    ),
    Check(
        name="raw_weather_hourly date is not null",
        sql="SELECT count(*) FROM raw_weather_hourly WHERE date IS NULL;",
    ),
    Check(
        name="raw_weather_hourly date is unique",
        sql="""
        SELECT count(*)
        FROM (
            SELECT date
            FROM raw_weather_hourly
            GROUP BY date
            HAVING count(*) > 1
        ) duplicates;
        """,
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate raw Berlin mobility tables in Postgres."
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("MOBILITY_DATABASE_URL"),
        help="Postgres connection URL. Defaults to MOBILITY_DATABASE_URL.",
    )
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or MOBILITY_DATABASE_URL is required")

    return args


def run_check(cursor, check: Check) -> int:
    cursor.execute(check.sql)
    return cursor.fetchone()[0]


def main() -> None:
    args = parse_args()
    failed_checks = []

    with psycopg2.connect(args.database_url) as connection:
        with connection.cursor() as cursor:
            for check in CHECKS:
                failure_count = run_check(cursor, check)
                status = "PASS" if failure_count == 0 else "FAIL"
                print(f"{status} {check.name}: {failure_count:,}")

                if failure_count:
                    failed_checks.append(check.name)

    if failed_checks:
        raise SystemExit(f"{len(failed_checks)} raw data checks failed.")

    print(f"All {len(CHECKS)} raw data checks passed.")


if __name__ == "__main__":
    main()
