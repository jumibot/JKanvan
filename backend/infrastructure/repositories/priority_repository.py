from datetime import datetime, timezone
from backend.domain.entities import Priority
from backend.domain.repositories import PriorityRepository
from backend.infrastructure.persistence.factory import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class SQLitePriorityRepository(PriorityRepository):

    def get_all(self) -> list[Priority]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM priorities ORDER BY id").fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_project(self, project_id: int) -> list[Priority]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM priorities WHERE project_id = ? ORDER BY id", (project_id,)
            ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, priority_id: int) -> Priority | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM priorities WHERE id = ?", (priority_id,)).fetchone()
        return self._to_entity(row) if row else None

    def create(self, priority: Priority) -> Priority:
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO priorities (name, icon, color, project_id) VALUES (?,?,?,?)",
                (priority.name, priority.icon, priority.color, priority.project_id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM priorities WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._to_entity(row)

    def update(self, priority: Priority) -> Priority:
        with get_connection() as conn:
            conn.execute(
                "UPDATE priorities SET name=?, icon=?, color=?, modified_at=? WHERE id=?",
                (priority.name, priority.icon, priority.color, _now(), priority.id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM priorities WHERE id = ?", (priority.id,)).fetchone()
        return self._to_entity(row)

    def delete(self, priority_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM priorities WHERE id = ?", (priority_id,))
            conn.commit()

    @staticmethod
    def _to_entity(row) -> Priority:
        keys = row.keys()
        def _opt(col): return row[col] if col in keys and row[col] is not None else None
        def _dt(col):
            v = _opt(col)
            return datetime.fromisoformat(v) if v else None
        return Priority(
            id=row["id"],
            name=row["name"],
            project_id=_opt("project_id"),
            icon=row["icon"],
            color=row["color"],
            created_at=_dt("created_at"),
            modified_at=_dt("modified_at"),
            created_by=_opt("created_by"),
            modified_by=_opt("modified_by"),
        )
