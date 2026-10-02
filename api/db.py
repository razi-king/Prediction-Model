"""
Cassandra access for the API: saves every prediction and returns the latest ones.

The API still works if Cassandra is down — predictions are served from the
models in memory, only the history feature is switched off.
"""
import json
import logging
import uuid
from datetime import datetime, timezone

log = logging.getLogger("devascend.db")


class PredictionStore:
    def __init__(self):
        self.session = None
        self.cluster = None

    def connect(self):
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
            self.session = None
            log.warning("Cassandra unavailable, history disabled: %s", exc)

    @property
    def available(self) -> bool:
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

    def latest(self, limit: int = 20) -> list[dict]:
        if not self.available:
            return []
        rows = self.session.execute(
            "SELECT created_at, role, country, years_pro, level, score, salary_usd, goal, months_to_goal "
            "FROM predictions WHERE bucket = 'all' LIMIT %s", (limit,))
        return [
            {**row._asdict(), "created_at": row.created_at.isoformat() + "Z"}
            for row in rows
        ]

    def close(self):
        if self.cluster:
            self.cluster.shutdown()
