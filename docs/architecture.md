# Arquitectura del backend

## Índice

- [Introducción a Clean Architecture](#introducción-a-clean-architecture)
- [Responsabilidades de cada capa](#responsabilidades-de-cada-capa)
  - [Domain](#domain-backenddomain)
  - [Application](#application-backendapplication)
  - [Infrastructure](#infrastructure-backendinfrastructure)
  - [Interfaces](#interfaces-backendinterfaces)
- [Flujo completo de una request](#flujo-completo-de-una-request)
- [Inyección de dependencias](#inyección-de-dependencias-dependenciespy)
- [Patrones notables](#patrones-notables)
- [Anexo: migrar de SQLite a PostgreSQL](#anexo-migrar-de-sqlite-a-postgresql)
  - [1. Dependencia](#1-dependencia)
  - [2. infrastructure/database.py](#2-infrastructuredatabasepy)
  - [3. Repositorios — diferencias SQL](#3-infrastructurerepositories---diferencias-sql)
  - [4. Schema DDL](#4-schema-ddl-infrastructuredatabasepy---init_db)
  - [5. Ajuste de booleanos](#5-_to_entity---ajuste-de-booleanos)
  - [Resumen del alcance](#resumen-del-alcance-del-cambio)

---

## Introducción a Clean Architecture

El backend sigue los principios de **Clean Architecture** (también conocida como arquitectura hexagonal o de puertos y adaptadores). La idea central es una sola regla: **las dependencias solo apuntan hacia dentro**. El núcleo del sistema (dominio y lógica de negocio) no sabe nada de frameworks, bases de datos ni HTTP; son las capas externas las que dependen del núcleo, nunca al revés.

```
           ┌─────────────────────────────────┐
           │         interfaces/             │  ← FastAPI, HTTP, JSON
           │  ┌───────────────────────────┐  │
           │  │      application/         │  │  ← casos de uso
           │  │  ┌─────────────────────┐  │  │
           │  │  │      domain/        │  │  │  ← entidades, contratos
           │  │  └─────────────────────┘  │  │
           │  └───────────────────────────┘  │
           └─────────────────────────────────┘
                infrastructure/  ←─────────────── implementa contratos de domain
```

**Por qué importa:** si el dominio y los casos de uso no dependen de SQLite ni de FastAPI, se pueden sustituir ambos sin tocar la lógica de negocio. Los tests unitarios de use cases no necesitan una base de datos real.

---

## Responsabilidades de cada capa

### Domain (`backend/domain/`)

**Es el núcleo. No importa nada externo — ni FastAPI, ni sqlite3, ni Pydantic.**

| Archivo | Responsabilidad |
|---------|----------------|
| `entities.py` | Dataclasses Python puras que representan los conceptos del negocio: `User`, `Project`, `Group`, `Task`, `Priority`, `Tag`, `TodoItem`. Sin lógica de persistencia ni validación HTTP. |
| `repositories.py` | ABCs (clases abstractas) que declaran los contratos de acceso a datos. Definen *qué* operaciones existen (`get_by_id`, `create`, `update`, `delete`…) sin decir *cómo* se implementan. |
| `exceptions.py` | 21 excepciones tipadas que representan violaciones de reglas de negocio (`ProjectLeaderRequired`, `TagNameAlreadyExists`, etc.). Son el único mecanismo de señalización de errores entre capas internas. |

**Regla:** nada en `domain/` tiene un `import` de fuera del propio paquete.

---

### Application (`backend/application/`)

**Orquesta la lógica de negocio. Depende de `domain/`, nada más.**

Contiene los *casos de uso*: cada módulo agrupa las operaciones de un recurso. Un caso de uso recibe repositorios por inyección de dependencias, invoca sus métodos y lanza excepciones de dominio si se viola alguna regla.

```python
# Ejemplo: lo que un use case puede y no puede hacer
class ProjectUseCases:
    def create(self, name, owner_id, leader_id, ...):
        # ✓ Consulta repositorios
        owner = self.user_repo.get_by_id(owner_id)
        # ✓ Lanza excepciones de dominio
        if owner is None:
            raise UserNotFound(owner_id)
        # ✓ Crea y persiste entidades
        project = Project(name=name, owner_id=owner_id, ...)
        return self.project_repo.create(project)
        # ✗ No importa sqlite3, FastAPI ni Pydantic
        # ✗ No lanza HTTPException
        # ✗ No conoce request/response bodies
```

| Módulo | Responsabilidad |
|--------|----------------|
| `user_use_cases.py` | Registro, login, CRUD usuarios, hashing PBKDF2 |
| `project_use_cases.py` | CRUD proyectos, gestión de miembros, cálculo de roles |
| `group_use_cases.py` | CRUD grupos kanban, reordenación de columnas |
| `task_use_cases.py` | CRUD tareas, asignación, reordenación dentro de grupo |
| `todo_use_cases.py` | CRUD subtareas (checklist de tarea) |
| `tag_use_cases.py` | CRUD etiquetas scoped al proyecto, asignación a tareas y grupos |
| `priority_use_cases.py` | CRUD prioridades scoped al proyecto |

---

### Infrastructure (`backend/infrastructure/`)

**Implementa los contratos de `domain/` con tecnología concreta. Es la única capa que conoce SQLite, JWT y detalles de I/O.**

| Archivo / carpeta | Responsabilidad |
|-------------------|----------------|
| `database.py` | Inicializa SQLite, crea las tablas con `CREATE TABLE IF NOT EXISTS`, ejecuta migraciones no destructivas en `_migrate()`, expone `get_connection()`. |
| `jwt_handler.py` | Codifica y decodifica tokens JWT HS256 con `PyJWT`. Expone `create_access_token(user_id)` y `decode_token(token) → user_id`. |
| `repositories/` | Una clase por entidad (`SQLiteUserRepository`, `SQLiteProjectRepository`, etc.) que implementa el ABC correspondiente de `domain/repositories.py` usando `sqlite3`. |

**Regla:** esta capa puede importar `domain/` y librerías externas (sqlite3, PyJWT). No importa `application/` ni `interfaces/`.

---

### Interfaces (`backend/interfaces/`)

**Adapta el mundo HTTP al interior del sistema. Traduce requests → llamadas a use cases → responses.**

| Archivo / carpeta | Responsabilidad |
|-------------------|----------------|
| `routers/` | Endpoints FastAPI. Reciben el HTTP request, llaman al use case correspondiente, capturan excepciones de dominio y las convierten en `HTTPException` con el código HTTP apropiado. |
| `schemas.py` | Modelos Pydantic para validar requests y serializar responses. Tienen métodos `.from_entity()` para convertir desde entidades de dominio. |
| `dependencies.py` | Fábricas de FastAPI `Depends()`: `get_current_user` (valida JWT), `require_admin`, `require_project_access`, `require_project_leader`, y factories que instancian repositorios y use cases. |

**Regla:** esta capa puede importar `application/`, `domain/` e `infrastructure/`. No contiene lógica de negocio.

---

## Flujo completo de una request

```
POST /tasks/  {group_id: 5, title: "Nueva tarea"}
  │
  ├─ FastAPI extrae el JWT del header
  ├─ Depends(get_current_user) → decode_token() → SQLiteUserRepository.get_by_id()
  ├─ Pydantic valida el body → TaskCreate
  │
  ├─ router/tasks.py llama a task_use_cases.create(group_id=5, title=..., ...)
  │     │
  │     ├─ application/task_use_cases.py
  │     │     ├─ group_repo.get_by_id(5)   → GroupNotFound si no existe → HTTPException 404
  │     │     ├─ Crea Task(group_id=5, title=...) 
  │     │     └─ task_repo.create(task) → devuelve Task con id asignado
  │     │           │
  │     │           └─ infrastructure/repositories/task_repository.py
  │     │                 └─ INSERT INTO tasks ... → SQLite
  │     │
  │     └─ devuelve Task entity
  │
  ├─ TaskResponse.from_entity(task) → JSON
  └─ HTTP 201
```

---

## Inyección de dependencias (`dependencies.py`)

FastAPI `Depends()` actúa como el contenedor de DI. Cada router declara sus dependencias como parámetros de función; FastAPI las resuelve antes de invocar el handler.

| Dependencia | Propósito |
|-------------|----------|
| `get_current_user` | Valida JWT Bearer → retorna `User` autenticado; 401 si inválido |
| `require_admin` | Verifica `user.is_admin`; 403 si no |
| `require_project_access` | Verifica owner/leader/member del proyecto; 403 si no |
| `require_project_leader` | Verifica owner o leader; 403 si no |
| `get_*_use_cases()` | Instancian use cases con sus repos concretos inyectados |

---

## Patrones notables

- **Sin ORM:** queries SQL escritas a mano en los repositorios. Evita N+1 con joins explícitos y da control total sobre el plan de ejecución.
- **Audit trail automático:** `created_at`, `modified_at`, `created_by`, `modified_by` se rellenan en los repositorios de infraestructura, no en el dominio.
- **Hard deletes + CASCADE:** no hay soft deletes; las FK tienen `ON DELETE CASCADE` / `ON DELETE SET NULL` según el caso.
- **Schemas ≠ Entities:** los schemas Pydantic solo existen en `interfaces/`. La conversión ocurre con `.from_entity()`, nunca en el dominio.
- **Primer admin automático:** si no existe ningún admin al arrancar, `_migrate()` promueve el primer usuario.

---

## Anexo: migrar de SQLite a PostgreSQL

La arquitectura limpia hace que este cambio esté **aislado en `infrastructure/`**. El dominio, los casos de uso y los routers no se tocan. Solo hay que intervenir en tres puntos.

### 1. Dependencia

```
# backend/requirements.txt — reemplazar (o añadir junto a sqlite3, que es stdlib):
psycopg2-binary>=2.9      # driver síncrono
# o para async:
asyncpg>=0.29
```

### 2. `infrastructure/database.py`

Este archivo es el único punto de configuración de la conexión.

**SQLite actual:**
```python
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "tasks.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
```

**PostgreSQL nuevo:**
```python
import os
import psycopg2
from psycopg2.extras import RealDictConnection   # equivalente a sqlite3.Row

DATABASE_URL = os.environ["DATABASE_URL"]
# Ej: "postgresql://user:password@host:5432/jkanban"

def get_connection() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(DATABASE_URL, connection_factory=RealDictConnection)
    return conn
```

`RealDictConnection` hace que las filas sean accesibles por nombre (`row["id"]`), igual que `sqlite3.Row`, por lo que los `_to_entity()` de los repositorios no cambian.

Para producción con alta concurrencia conviene usar un pool:
```python
from psycopg2 import pool as pg_pool

_pool = pg_pool.ThreadedConnectionPool(2, 10, DATABASE_URL)

def get_connection():
    conn = _pool.getconn()
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    try:
        yield conn
    finally:
        _pool.putconn(conn)
```

### 3. `infrastructure/repositories/*.py` — diferencias SQL

Hay cuatro diferencias concretas entre SQLite y PostgreSQL que afectan a los repositorios:

| Aspecto | SQLite | PostgreSQL |
|---------|--------|-----------|
| **Placeholder de parámetros** | `?` | `%s` |
| **ID del registro insertado** | `cursor.lastrowid` | `RETURNING id` + `fetchone()[0]` |
| **Booleanos** | `INTEGER` (0/1), `int(bool)` en escritura, `bool(row[col])` en lectura | `BOOLEAN` nativo, sin conversión |
| **FK enforcement** | `PRAGMA foreign_keys = ON` (por conexión) | Activo por defecto; no necesita pragma |

#### Ejemplo concreto: `user_repository.py`

```python
# ── SQLite ──────────────────────────────────────────────
def create(self, user: User) -> User:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash, avatar_url) VALUES (?,?,?,?)",
            (user.name, user.email, user.password_hash, user.avatar_url),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = ?",
                           (cursor.lastrowid,)).fetchone()
    return self._to_entity(row)

# ── PostgreSQL ───────────────────────────────────────────
def create(self, user: User) -> User:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO users (name, email, password_hash, avatar_url)
                   VALUES (%s, %s, %s, %s) RETURNING id""",
                (user.name, user.email, user.password_hash, user.avatar_url),
            )
            new_id = cur.fetchone()["id"]
            cur.execute("SELECT * FROM users WHERE id = %s", (new_id,))
            row = cur.fetchone()
        conn.commit()
    return self._to_entity(row)
```

El patrón es sistemático: `?` → `%s` en todas las queries, `cursor.lastrowid` → `RETURNING id`.

### 4. Schema DDL (`infrastructure/database.py` — `init_db`)

Las definiciones de tabla necesitan ajustes menores:

| SQLite | PostgreSQL |
|--------|-----------|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` (o `BIGSERIAL`) |
| `TEXT NOT NULL DEFAULT (datetime('now'))` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` |
| `TEXT` para fechas | `TIMESTAMPTZ` |
| `INTEGER NOT NULL DEFAULT 0 CHECK(is_admin IN (0,1))` | `BOOLEAN NOT NULL DEFAULT FALSE` |
| `CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#')` | `CHECK(color ~ '^#[0-9A-Fa-f]{6}$')` |
| `INSERT OR IGNORE INTO ...` | `INSERT INTO ... ON CONFLICT DO NOTHING` |

Ejemplo de tabla `users` en PostgreSQL:
```sql
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    name          TEXT         NOT NULL,
    email         TEXT         NOT NULL UNIQUE,
    password_hash TEXT         NOT NULL,
    avatar_url    TEXT,
    is_admin      BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    modified_at   TIMESTAMPTZ,
    created_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    modified_by   INTEGER REFERENCES users(id) ON DELETE SET NULL
);
```

### 5. `_to_entity()` — ajuste de booleanos

Con PostgreSQL y `RealDictCursor`, los booleanos ya llegan como `True`/`False` nativos. Hay que eliminar la conversión manual:

```python
# SQLite:
is_admin=bool(row["is_admin"]) if "is_admin" in keys else False,

# PostgreSQL (bool nativo, sin conversión):
is_admin=row.get("is_admin", False),
```

### Resumen del alcance del cambio

| Capa | Cambios |
|------|---------|
| `domain/` | **Ninguno** |
| `application/` | **Ninguno** |
| `interfaces/` | **Ninguno** |
| `infrastructure/database.py` | Driver, `get_connection()`, DDL de tablas |
| `infrastructure/repositories/*.py` | `?` → `%s`, `lastrowid` → `RETURNING id`, conversiones de bool |
| `requirements.txt` | Añadir `psycopg2-binary` |

El cambio es completamente mecánico y localizado. Si en algún momento se quisiera soportar ambas bases de datos simultáneamente (tests con SQLite, producción con PostgreSQL), bastaría con tener dos implementaciones de `get_connection()` seleccionadas por variable de entorno, sin tocar nada más.
