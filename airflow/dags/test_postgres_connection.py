from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator

with DAG(
    dag_id="test_postgres_connection",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["debug", "infra"],
) as dag:
    create_table = PostgresOperator(
        task_id="create_table",
        postgres_conn_id="mobility_postgres",
        sql="""
        CREATE TABLE IF NOT EXISTS airflow_smoketest (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
    )

    insert_row = PostgresOperator(
        task_id="insert_row",
        postgres_conn_id="mobility_postgres",
        sql="INSERT INTO airflow_smoketest DEFAULT VALUES;",
    )

    create_table >> insert_row