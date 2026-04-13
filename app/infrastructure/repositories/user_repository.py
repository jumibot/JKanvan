from datetime import datetime, timezone
from app.domain.entities import User
from app.domain.repositories import UserRepository
from app.infrastructure.database import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class SQLiteUserRepository(UserRepository):

    def get_all(self) -> list[User]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, user_id: int) -> User | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self._to_entity(row) if row else None

    def get_by_email(self, email: str) -> User | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return self._to_entity(row) if row else None

    def create(self, user: User) -> User:
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash, avatar_url) VALUES (?,?,?,?)",
                (user.name, user.email, user.password_hash, user.avatar_url),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._to_entity(row)

    def update(self, user: User) -> User:
        with get_connection() as conn:
            conn.execute(
                """UPDATE users
                   SET name=?, email=?, password_hash=?, avatar_url=?, is_admin=?, modified_at=?
                   WHERE id=?""",
                (user.name, user.email, user.password_hash, user.avatar_url, int(user.is_admin), _now(), user.id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user.id,)).fetchone()
        return self._to_entity(row)

    def delete(self, user_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()

    def count_owned_projects(self, user_id: int) -> int:
        with get_connection() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM projects WHERE owner_id = ?", (user_id,)
            ).fetchone()[0]

    @staticmethod
    def _to_entity(row) -> User:
        keys = row.keys()
        def _opt(col): return row[col] if col in keys and row[col] else None
        def _dt(col):
            v = _opt(col)
            return datetime.fromisoformat(v) if v else None
        return User(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            password_hash=row["password_hash"],
            avatar_url=_opt("avatar_url"),
            is_admin=bool(row["is_admin"]) if "is_admin" in keys else False,
            created_at=_dt("created_at"),
            modified_at=_dt("modified_at"),
            created_by=_opt("created_by"),
            modified_by=_opt("modified_by"),
        )
