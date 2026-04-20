from backend.config import db_settings


def get_connection():
    """Return an open connection for the configured DB engine."""
    engine = db_settings.engine
    if engine == "sqlite":
        from backend.infrastructure.persistence.sqlite.connection import (
            get_connection as _sqlite,
        )
        return _sqlite()
    raise ValueError(f"Unsupported DB engine: {engine!r}")


def init_engine() -> None:
    """Create schema, run migrations, and seed demo data for the configured engine."""
    engine = db_settings.engine
    if engine == "sqlite":
        from backend.infrastructure.persistence.sqlite.migrations import migrate
        from backend.infrastructure.persistence.sqlite.schema import create_schema
        from backend.infrastructure.persistence.sqlite.seed import seed_db

        with get_connection() as conn:
            create_schema(conn)
            migrate(conn)
            conn.commit()
        seed_db()
        return
    raise ValueError(f"Unsupported DB engine: {engine!r}")
