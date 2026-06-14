FROM apache/airflow:2.8.1-python3.11

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir \
    -r /tmp/requirements.txt \
    apache-airflow-providers-postgres

RUN python -m venv /opt/airflow/dbt_venv \
    && PIP_USER=false /opt/airflow/dbt_venv/bin/pip install --no-cache-dir \
        dbt-core==1.10.22 \
        dbt-postgres==1.9.1
