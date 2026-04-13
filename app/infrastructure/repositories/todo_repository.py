from datetime import datetime, timezone
from app.domain.entities import TodoItem
from app.domain.repositories import TodoRepository
from app.infrastructure.database import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class SQLiteTodoRepository(TodoRepository):

    def get_by_task(self, task_id: int) -> list[TodoItem]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM todo_items WHERE task_id=? ORDER BY sort_order, id",
                (task_id,),
            ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, todo_id: int) -> TodoItem | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM todo_items WHERE id=?", (todo_id,)).fetchone()
        return self._to_entity(row) if row else None

    def create(self, todo: TodoItem) -> TodoItem:
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO todo_items (task_id, title, completed, sort_order) VALUES (?,?,?,?)",
                (todo.task_id, todo.title, int(todo.completed), todo.order),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM todo_items WHERE id=?", (cursor.lastrowid,)).fetchone()
        return self._to_entity(row)

    def update(self, todo: TodoItem) -> TodoItem:
        with get_connection() as conn:
            conn.execute(
                "UPDATE todo_items SET title=?, completed=?, sort_order=?, modified_at=? WHERE id=?",
                (todo.title, int(todo.completed), todo.order, _now(), todo.id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM todo_items WHERE id=?", (todo.id,)).fetchone()
        return self._to_entity(row)

    def delete(self, todo_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM todo_items WHERE id=?", (todo_id,))
            conn.commit()

    @staticmethod
    def _to_entity(row) -> TodoItem:
        keys = row.keys()
        def _opt(col): return row[col] if col in keys and row[col] is not None else None
        def _dt(col):
            v = _opt(col)
            return datetime.fromisoformat(v) if v else None
        return TodoItem(
            id=row["id"],
            task_id=row["task_id"],
            title=row["title"],
            completed=bool(row["completed"]),
            order=row["sort_order"],
            created_at=_dt("created_at"),
            modified_at=_dt("modified_at"),
            created_by=_opt("created_by"),
            modified_by=_opt("modified_by"),
        )
