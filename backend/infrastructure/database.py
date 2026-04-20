from backend.infrastructure.persistence.sqlite.connection import get_connection
from backend.infrastructure.persistence.sqlite.schema import create_schema
from backend.infrastructure.persistence.sqlite.migrations import migrate
from backend.infrastructure.persistence.sqlite.seed import seed_db


def init_db() -> None:
    with get_connection() as conn:
        create_schema(conn)
        migrate(conn)
        conn.commit()
    seed_db()


__all__ = ["get_connection", "init_db"]
