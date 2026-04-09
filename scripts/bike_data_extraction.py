from pathlib import Path
import pandas as pd


FILE_PATH = (
    "https://www.berlin.de/sen/uvk/_assets/verkehr/verkehrsplanung/radverkehr/weitere-radinfrastruktur/zaehlstellen-und-fahrradbarometer/gesamtdatei-stundenwerte.xlsx"
)

OUTPUT_PATH_BIKE_COUNTS = Path("mobility_long.csv")
OUTPUT_PATH_STATION_METADATA = Path("mobility_metadata.csv")


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
        value_name="bike_count"
    )

    long_df = long_df[long_df["bike_count"].notna()].copy()
    long_df["observed_at"] = pd.to_datetime(
        long_df["observed_at"],
        errors="coerce",
        dayfirst=True
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
        dayfirst=True
    )
    
    return df


def main() -> None:
    bike_counts = load_bike_counts(FILE_PATH, start_year=2025, end_year=2025)
    station_metadata = load_station_metadata(FILE_PATH)

    bike_counts.to_csv(OUTPUT_PATH_BIKE_COUNTS, index=False)
    station_metadata.to_csv(OUTPUT_PATH_STATION_METADATA, index=False)


if __name__ == "__main__":
    main()