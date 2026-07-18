import os

import psycopg2


def _positive_int(name, default):
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return 0
    return value if value > 0 else 0


def maintenance_probe():
    stale_seconds = _positive_int("HYDRA_MAINTENANCE_STALE_SECONDS", 120)
    max_failures = _positive_int("HYDRA_MAINTENANCE_MAX_FAILURES", 5)
    if not stale_seconds or not max_failures:
        return False
    try:
        with psycopg2.connect(
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            host=os.environ["DB_HOST"],
            port=os.environ.get("DB_PORT", "5432"),
            connect_timeout=5,
            options="-c statement_timeout=5000",
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        heartbeat_at >= CURRENT_TIMESTAMP - (%s * INTERVAL '1 second'),
                        consecutive_failures < %s
                    FROM hydra_ops_maintenancestate
                    WHERE key = 'primary'
                    """,
                    (stale_seconds, max_failures),
                )
                row = cursor.fetchone()
    except (KeyError, psycopg2.Error):
        return False
    return row == (True, True)


if __name__ == "__main__":
    raise SystemExit(0 if maintenance_probe() else 1)
