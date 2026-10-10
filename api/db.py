"""
Cassandra access for the API: saves every prediction and returns the latest ones.

The API still works if Cassandra is down — predictions are served from the
models in memory, only the history feature is switched off.
"""
import json
import logging
import time
import uuid
from datetime import datetime, timezone

log = logging.getLogger("devascend.db")

# If Cassandra was unreachable (e.g. Astra DB hibernating on the free plan while the API started),
# try to connect again at most once per minute instead of staying disconnected until the next restart.
RETRY_SECONDS = 60


class PredictionStore:
    def __init__(self):
        self.session = None
        self.cluster = None
        self._last_attempt = 0.0

    def connect(self):
        self._last_attempt = time.monotonic()
        try:
            # from ml/: the same connection + schema code as the pipeline
            # (local Docker Cassandra, or Astra DB in the cloud when ASTRA_DB_TOKEN is set)
            from cassandra_db import USING_ASTRA, create_schema, make_cluster

            self.cluster = make_cluster(connect_timeout=10 if USING_ASTRA else 5)
            self.session = self.cluster.connect()
            create_schema(self.session)                       # makes sure tables exist
            self._insert = self.session.prepare(
                "INSERT INTO predictions (bucket, created_at, id, role, country, years_pro, level, "
                "score, salary_usd, goal, months_to_goal, profile_json) "
                "VALUES ('all', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            )
            log.info("Connected to Cassandra (%s)", "Astra DB cloud" if USING_ASTRA else "local")
        except Exception as exc:
            self._disconnect()
            log.warning("Cassandra unavailable, history disabled (retrying in %ss): %s", RETRY_SECONDS, exc)

    def _disconnect(self):
        if self.cluster:
            try:
                self.cluster.shutdown()
            except Exception:
                pass
        self.session = None
        self.cluster = None

    def _reconnect_if_due(self):
        if self.session is None and time.monotonic() - self._last_attempt >= RETRY_SECONDS:
            self.connect()

    @property
    def available(self) -> bool:
        self._reconnect_if_due()
        return self.session is not None

    def save(self, profile: dict, result: dict, growth: dict):
        if not self.available:
            return
        try:
            self.session.execute(self._insert, (
                datetime.now(timezone.utc), uuid.uuid4(), profile["role"], profile["country"],
                float(profile["years_pro"]), result["level"], float(result["score"]),
                float(result["salary_usd"]), growth["time_to_goal"]["goal"],
                growth["time_to_goal"]["months_with_plan"], json.dumps(profile),
            ))
        except Exception as exc:
            log.warning("Could not save prediction: %s", exc)
            self._disconnect()  # the connection may be dead (database hibernated); reconnect later

    def latest(self, limit: int = 20) -> list[dict]:
        if not self.available:
            return []
        try:
            rows = self.session.execute(
                "SELECT created_at, role, country, years_pro, level, score, salary_usd, goal, months_to_goal "
                "FROM predictions WHERE bucket = 'all' LIMIT %s", (limit,))
        except Exception as exc:
            log.warning("Could not read history: %s", exc)
            self._disconnect()
            return []
        return [
            {**row._asdict(), "created_at": row.created_at.isoformat() + "Z"}
            for row in rows
        ]

    def close(self):
        if self.cluster:
            self.cluster.shutdown()
