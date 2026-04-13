import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Patch DB_PATH BEFORE importing app.main (main.py llama init_db() al importar)
import app.infrastructure.database as db_module

_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
db_module.DB_PATH = Path(_tmp_db.name)

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth(client: TestClient):
    """Creates a fresh test user and returns (user_data, auth_headers).
    Runs after clean_db so the user is the only one in the DB.
    """
    r = client.post("/users/", json={
        "name": "AuthUser", "email": "_auth@test.com", "password": "authpass123",
    })
    user = r.json()
    lr = client.post("/auth/login", json={"email": "_auth@test.com", "password": "authpass123"})
    token = lr.json()["access_token"]
    return user, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth(client: TestClient):
    """Creates a test admin user and returns (user_data, auth_headers)."""
    r = client.post("/users/", json={
        "name": "AdminUser", "email": "_admin@test.com", "password": "adminpass123",
    })
    user = r.json()
    with db_module.get_connection() as conn:
        conn.execute("UPDATE users SET is_admin=1 WHERE id=?", (user["id"],))
        conn.commit()
    lr = client.post("/auth/login", json={"email": "_admin@test.com", "password": "adminpass123"})
    token = lr.json()["access_token"]
    user["is_admin"] = True
    return user, {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def clean_db():
    """Vacía todas las tablas antes de cada test respetando el orden FK."""
    with db_module.get_connection() as conn:
        conn.execute("DELETE FROM todo_items")
        conn.execute("DELETE FROM task_tags")
        conn.execute("DELETE FROM group_tags")
        conn.execute("DELETE FROM tasks")
        conn.execute("DELETE FROM tags")
        conn.execute("DELETE FROM project_members")
        conn.execute("DELETE FROM groups")
        conn.execute("DELETE FROM projects")
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM priorities")
        for tbl in (
            "todo_items", "task_tags", "group_tags", "tasks", "tags",
            "project_members", "groups", "projects", "users", "priorities",
        ):
            conn.execute("DELETE FROM sqlite_sequence WHERE name=?", (tbl,))
        conn.commit()
