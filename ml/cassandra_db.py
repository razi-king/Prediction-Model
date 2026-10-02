"""
Small helper for talking to Cassandra.

Cassandra basics used in this project:
  * KEYSPACE  = like a "database" in MySQL. Ours is called `devascend`.
  * TABLE     = rows + columns, but every table needs a PRIMARY KEY.
  * PARTITION KEY (first part of the primary key) decides which node stores the row.
    We partition survey rows by `survey_year`, so "give me all 2024 rows" is one fast query.
  * CLUSTERING KEY (rest of the primary key) sorts rows inside a partition.

Two places Cassandra can live:
  * LOCAL  - Docker on your laptop (docker-compose.yml), used for development and training.
  * CLOUD  - DataStax Astra DB (managed Apache Cassandra), used when the app is deployed.
             Activated by the ASTRA_DB_* environment variables (see config.py / docs/10-deployment.md).
"""
import base64
import tempfile
import time
from pathlib import Path

from cassandra.cluster import Cluster

from config import (ASTRA_DB_SECURE_BUNDLE, ASTRA_DB_SECURE_BUNDLE_B64, ASTRA_DB_TOKEN,
                    CASSANDRA_HOSTS, CASSANDRA_PORT, KEYSPACE)

USING_ASTRA = bool(ASTRA_DB_TOKEN)


def _secure_bundle_path() -> str:
    """Astra needs its 'secure connect bundle' zip as a FILE. Hosting secrets are text, so we
    also accept the zip as base64 and write it to a temporary file."""
    if ASTRA_DB_SECURE_BUNDLE:
        return ASTRA_DB_SECURE_BUNDLE
    if ASTRA_DB_SECURE_BUNDLE_B64:
        path = Path(tempfile.gettempdir()) / "astra_secure_connect_bundle.zip"
        path.write_bytes(base64.b64decode(ASTRA_DB_SECURE_BUNDLE_B64))
        return str(path)
    raise RuntimeError("ASTRA_DB_TOKEN is set but no secure connect bundle was given "
                       "(set ASTRA_DB_SECURE_BUNDLE or ASTRA_DB_SECURE_BUNDLE_B64)")


def make_cluster(connect_timeout: int = 10) -> Cluster:
    """A Cluster object for Astra (cloud) or the local Docker Cassandra."""
    if USING_ASTRA:
        from cassandra.auth import PlainTextAuthProvider

        # Astra login: the user name is literally "token", the password is the AstraCS:... token
        return Cluster(cloud={"secure_connect_bundle": _secure_bundle_path()},
                       auth_provider=PlainTextAuthProvider("token", ASTRA_DB_TOKEN),
                       connect_timeout=connect_timeout)
    return Cluster(CASSANDRA_HOSTS, port=CASSANDRA_PORT, connect_timeout=connect_timeout)

SCHEMA = [
    f"""
    CREATE KEYSPACE IF NOT EXISTS {KEYSPACE}
    WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
    """,
    # Raw survey answers (one row = one developer). Query pattern: all rows of a given year.
    f"""
    CREATE TABLE IF NOT EXISTS {KEYSPACE}.survey_responses (
        survey_year     int,
        response_id     int,
        main_branch     text,
        employment      text,
        country         text,
        ed_level        text,
        years_code      text,
        years_code_pro  text,
        dev_type        text,
        languages       text,
        platforms       text,
        webframes       text,
        databases       text,
        tools           text,
        misc_tech       text,
        ai_select       text,
        salary_usd      double,
        PRIMARY KEY ((survey_year), response_id)
    )
    """,
    # Every prediction made by the web app. Query pattern: latest N predictions.
    # All rows share bucket='all' and are sorted newest-first by created_at.
    f"""
    CREATE TABLE IF NOT EXISTS {KEYSPACE}.predictions (
        bucket        text,
        created_at    timestamp,
        id            uuid,
        role          text,
        country       text,
        years_pro     double,
        level         text,
        score         double,
        salary_usd    double,
        goal          text,
        months_to_goal int,
        profile_json  text,
        PRIMARY KEY ((bucket), created_at, id)
    ) WITH CLUSTERING ORDER BY (created_at DESC, id ASC)
    """,
]


def connect(retries: int = 20, wait_seconds: int = 6):
    """Connect to Cassandra, retrying while the container is still booting."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            cluster = make_cluster()
            session = cluster.connect()
            return cluster, session
        except Exception as exc:  # NoHostAvailable while Cassandra starts up
            last_error = exc
            print(f"  Cassandra not ready (attempt {attempt}/{retries}), retrying in {wait_seconds}s...")
            time.sleep(wait_seconds)
    raise RuntimeError(
        "Could not connect to Cassandra. Is it running?  ->  docker compose up -d"
    ) from last_error


def create_schema(session):
    for statement in SCHEMA:
        if USING_ASTRA and "CREATE KEYSPACE" in statement:
            continue  # on Astra the keyspace is created in the Astra web console, not with CQL
        session.execute(statement)
    session.set_keyspace(KEYSPACE)
    # Columns added after the first version of the table (ALTER fails harmlessly if it already exists)
    try:
        session.execute("ALTER TABLE survey_responses ADD ai_select text")
    except Exception:
        pass
