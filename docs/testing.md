# Tests

## Índice

- [Setup](#setup-testsconftestpy)
- [Archivos de test](#archivos-de-test)
- [Patrón de test típico](#patrón-de-test-típico)
- [Ejecución](#ejecución)
- [Notas importantes](#notas-importantes)

---

## Setup (`tests/conftest.py`)

- **Framework:** Pytest + `httpx.TestClient` (FastAPI)
- **Base de datos de test:** SQLite en memoria (`:memory:`) — independiente de `tasks.db`
- **Fixtures principales:**

| Fixture | Scope | Descripción |
|---------|-------|-------------|
| `client` | session | `TestClient(app)` con BD temporal |
| `auth` | function | Crea usuario de test + retorna `(user, headers)` |
| `admin_auth` | function | Crea usuario admin + retorna `(user, headers)` |
| `clean_db` | function (autouse) | Trunca todas las tablas antes de cada test (respeta orden FK) |

El fixture `auth` devuelve `(user_dict, {"Authorization": "Bearer <token>"})`.

---

## Archivos de test

| Archivo | Qué cubre |
|---------|-----------|
| `test_auth.py` | Login correcto, credenciales incorrectas, validación de campos |
| `test_users.py` | CRUD usuarios, auto-delete, permisos (propio vs admin) |
| `test_projects.py` | CRUD proyectos, miembros, roles, deletion preview, cascade delete |
| `test_groups.py` | CRUD grupos, reordenación, FK con proyecto |
| `test_tasks.py` | CRUD tareas, asignación user/priority/tags, reordenación |
| `test_todos.py` | CRUD subtareas, orden, FK con tarea |
| `test_tags.py` | CRUD etiquetas, unicidad por proyecto, asignación a tareas |
| `test_priorities.py` | CRUD prioridades, unicidad por proyecto |
| `test_admin.py` | Panel admin: deletion preview, cascade delete con contraseña |
| `test_resources.py` | Endpoints legacy `/resources/` |

---

## Patrón de test típico

```python
def test_create_task(auth):
    user, headers = auth
    # Crear dependencias necesarias
    project = client.post("/projects/", json={...}, headers=headers).json()
    group   = client.post("/groups/", json={"project_id": project["id"], ...}, headers=headers).json()
    # Acción bajo test
    r = client.post("/tasks/", json={"group_id": group["id"], "title": "Test"}, headers=headers)
    # Assertions
    assert r.status_code == 201
    assert r.json()["title"] == "Test"

def test_unauthorized(auth):
    _, headers = auth
    r = client.get("/admin/users/1/deletion-preview", headers=headers)
    assert r.status_code == 403
```

---

## Ejecución

```bash
# Todos los tests
pytest

# Con detalle
pytest -v

# Un archivo concreto
pytest tests/test_projects.py

# Un test concreto
pytest tests/test_projects.py::test_cascade_delete -v

# Con cobertura (requiere pytest-cov)
pytest --cov=app --cov-report=term-missing
```

---

## Notas importantes

- Los tests **no usan mocks de base de datos** — cada test corre contra una BD SQLite real en memoria para garantizar que las queries SQL y las cascadas FK funcionan como en producción.
- `clean_db` trunca en el orden correcto para respetar FK constraints: `task_tags → todo_items → tasks → groups → project_members → projects → priorities → tags → users`.
- Los tests de admin requieren el fixture `admin_auth` (usuario con `is_admin=True`).
- El `TestClient` de FastAPI levanta la app completa incluida la inicialización de BD — no hay que arrancar el servidor por separado.
