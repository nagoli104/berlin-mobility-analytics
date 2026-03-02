## Local Development

This project uses Docker Compose to run:

- PostgreSQL (metadata + analytics database)
- Apache Airflow (webserver + scheduler)
- Metabase (BI dashboard)

All services are configured via a `.env` file located in the project root.

---

### 1️⃣ Environment Setup

Create a local `.env` file based on `.env.example`:

    cp .env.example .env

Adjust values if needed.

⚠️ The `.env` file is not committed to the repository.

---

### 2️⃣ First-Time Bootstrap (Airflow Metadata Initialization)

On first startup, initialize the Airflow metadata database and create the admin user:

    docker compose --env-file .env -f docker/docker-compose.yml up airflow-init

Wait until the container exits with:

    Exited (0)

This step:
- Migrates the Airflow metadata database
- Creates the Admin user

---

### 3️⃣ Start All Services

    docker compose --env-file .env -f docker/docker-compose.yml up -d

Verify running containers:

    docker ps

---

### 4️⃣ Access the Services

| Service    | URL                     |
|------------|-------------------------|
| Airflow UI | http://localhost:8080   |
| Metabase   | http://localhost:3000   |
| Postgres   | localhost:5432          |

Airflow login credentials are defined in `.env`.

---

### 5️⃣ PostgreSQL Quick Verification

Connect to the database:

    docker exec -it mobility_postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}

Check connection:

    \conninfo

Test persistence:

    CREATE TABLE test_table (id INT);

Restart services:

    docker compose --env-file .env -f docker/docker-compose.yml down
    docker compose --env-file .env -f docker/docker-compose.yml up -d postgres

Reconnect and verify:

    \dt

The table should still exist, confirming volume persistence.

---

### 6️⃣ Stop Services

    docker compose --env-file .env -f docker/docker-compose.yml down

To remove volumes (⚠️ deletes database data):

    docker compose --env-file .env -f docker/docker-compose.yml down -v

---

## Project Architecture (Local)

Host (Mac)
│
├─ Port 8080 → Airflow Webserver
├─ Port 3000 → Metabase
├─ Port 5432 → PostgreSQL
│
└─ Docker Network (mobility_net)
    ├─ postgres
    ├─ airflow_webserver
    ├─ airflow_scheduler
    └─ metabase

Airflow connects internally to Postgres via the Docker network using the service name `postgres`.

---

## Notes

- Airflow metadata is stored in PostgreSQL.
- `.env` variables are injected using `--env-file`.
- The `airflow-init` service is a one-time bootstrap container.
- This setup is intended for local development only.