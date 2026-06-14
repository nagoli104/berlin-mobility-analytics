from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.models.param import Param
from airflow.operators.bash import BashOperator


PROJECT_DIR = "/opt/airflow"
DATA_DIR = f"{PROJECT_DIR}/data"
DBT_PROJECT_DIR = f"{PROJECT_DIR}/dbt/berlin_mobility"
DBT_BIN = "/opt/airflow/dbt_venv/bin/dbt"


with DAG(
    dag_id="mobility_raw_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["mobility", "raw", "dbt"],
    params={
        "bike_start_year": Param(2025, type="integer"),
        "bike_end_year": Param(2025, type="integer"),
        "weather_latitude": Param(52.52, type="number"),
        "weather_longitude": Param(13.405, type="number"),
        "weather_start_date": Param("2025-01-01", type="string"),
        "weather_end_date": Param("2025-12-31", type="string"),
    },
) as dag:
    extract_bike_data = BashOperator(
        task_id="extract_bike_data",
        bash_command=(
            "python /opt/airflow/scripts/bike_data_extraction.py "
            "--start-year {{ params.bike_start_year }} "
            "--end-year {{ params.bike_end_year }} "
            f"--output-counts {DATA_DIR}/mobility_long.csv "
            f"--output-metadata {DATA_DIR}/mobility_metadata.csv"
        ),
    )

    extract_weather_data = BashOperator(
        task_id="extract_weather_data",
        bash_command=(
            "python /opt/airflow/scripts/openmeteo_weather_export.py "
            "--latitude {{ params.weather_latitude }} "
            "--longitude {{ params.weather_longitude }} "
            "--start-date {{ params.weather_start_date }} "
            "--end-date {{ params.weather_end_date }} "
            f"--output {DATA_DIR}/weather_data.csv "
            f"--cache-path {DATA_DIR}/.openmeteo_cache"
        ),
    )

    load_raw_tables = BashOperator(
        task_id="load_raw_tables",
        bash_command=(
            "python /opt/airflow/scripts/load_csv_to_postgres.py "
            f"--counts {DATA_DIR}/mobility_long.csv "
            f"--metadata {DATA_DIR}/mobility_metadata.csv "
            f"--weather {DATA_DIR}/weather_data.csv"
        ),
    )

    validate_raw_tables = BashOperator(
        task_id="validate_raw_tables",
        bash_command="python /opt/airflow/scripts/validate_raw_data.py",
    )

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"{DBT_BIN} deps --project-dir {DBT_PROJECT_DIR}",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"{DBT_BIN} run --project-dir {DBT_PROJECT_DIR} "
            f"--profiles-dir {DBT_PROJECT_DIR}"
        ),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"{DBT_BIN} test --project-dir {DBT_PROJECT_DIR} "
            f"--profiles-dir {DBT_PROJECT_DIR}"
        ),
    )

    [extract_bike_data, extract_weather_data] >> load_raw_tables
    load_raw_tables >> validate_raw_tables >> dbt_deps >> dbt_run >> dbt_test
