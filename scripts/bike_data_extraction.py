#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_FILE_PATH = (
    "https://www.berlin.de/sen/uvk/_assets/verkehr/verkehrsplanung/radverkehr/weitere-radinfrastruktur/zaehlstellen-und-fahrradbarometer/gesamtdatei-stundenwerte.xlsx"
)

DEFAULT_OUTPUT_PATH_BIKE_COUNTS = Path("mobility_long.csv")
DEFAULT_OUTPUT_PATH_STATION_METADATA = Path("mobility_metadata.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and reshape Berlin hourly bike count data."
    )
    parser.add_argument(
        "--file-path",
        default=DEFAULT_FILE_PATH,
        help="Source Excel workbook URL or local path.",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2025,
        help="First yearly sheet to extract.",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2025,
        help="Last yearly sheet to extract.",
    )
    parser.add_argument(
        "--output-counts",
        type=Path,
        default=DEFAULT_OUTPUT_PATH_BIKE_COUNTS,
        help="Output CSV path for long-format bike counts.",
    )
    parser.add_argument(
        "--output-metadata",
        type=Path,
        default=DEFAULT_OUTPUT_PATH_STATION_METADATA,
        help="Output CSV path for station metadata.",
    )

    args = parser.parse_args()
    if args.start_year > args.end_year:
        parser.error("--start-year must be less than or equal to --end-year")

    return args


def build_sheet_names(start_year: int, end_year: int) -> list[str]:
    """Return Excel sheet names for the given year range [start_year, end_year]."""
    return [f"Jahresdatei {year}" for year in range(start_year, end_year + 1)]


def clean_station_headers(columns) -> list[str]:
    """
    Clean station column headers by removing installation date suffixes.
    Keeps the first column as 'observed_at'.
    """
    station_cols = [col.split("\n")[0].split(" ")[0] for col in list(columns)[1:]]
    return ["observed_at", *station_cols]


def read_count_sheet(file_path: str, sheet_name: str) -> pd.DataFrame:
    """Read and transform one yearly count sheet into long format."""
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    df.columns = clean_station_headers(df.columns)

    long_df = df.melt(
        id_vars="observed_at",
        var_name="station_id",
        value_name="bike_count",
    )

    long_df = long_df[long_df["bike_count"].notna()].copy()
    long_df["observed_at"] = pd.to_datetime(
        long_df["observed_at"],
        errors="coerce",
        dayfirst=True,
    )

    return long_df


def load_bike_counts(file_path: str, start_year: int, end_year: int) -> pd.DataFrame:
    """Load and concatenate bike count data for multiple years."""
    sheet_names = build_sheet_names(start_year, end_year)
    frames = [read_count_sheet(file_path, sheet) for sheet in sheet_names]
    return pd.concat(frames, ignore_index=True, copy=False)


def extract_direction(description: pd.Series) -> pd.Series:
    """Infer direction from station description."""
    direction_map = {
        "West": "west",
        "Ost": "east",
        "Nord": "north",
        "Süd": "south",
    }

    direction = pd.Series(pd.NA, index=description.index, dtype="string")

    for suffix, value in direction_map.items():
        mask = description.str.endswith(suffix, na=False)
        direction.loc[mask] = value

    return direction


def load_station_metadata(file_path: str) -> pd.DataFrame:
    """Load and enrich station metadata."""
    df = pd.read_excel(file_path, sheet_name="Standortdaten")
    df.columns = ["station_id", "description", "latitude", "longitude", "installed"]
    df["direction"] = extract_direction(df["description"])

    df["installed"] = pd.to_datetime(
        df["installed"],
        errors="coerce",
        dayfirst=True,
    )

    return df


def main() -> None:
    args = parse_args()

    bike_counts = load_bike_counts(
        args.file_path,
        start_year=args.start_year,
        end_year=args.end_year,
    )
    station_metadata = load_station_metadata(args.file_path)

    args.output_counts.parent.mkdir(parents=True, exist_ok=True)
    args.output_metadata.parent.mkdir(parents=True, exist_ok=True)

    bike_counts.to_csv(args.output_counts, index=False)
    station_metadata.to_csv(args.output_metadata, index=False)

    print(f"Saved {len(bike_counts):,} bike count rows to {args.output_counts}")
    print(f"Saved {len(station_metadata):,} station rows to {args.output_metadata}")


if __name__ == "__main__":
    main()
