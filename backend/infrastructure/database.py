import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "tasks.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                email         TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                avatar_url    TEXT,
                is_admin      INTEGER NOT NULL DEFAULT 0 CHECK(is_admin IN (0,1)),
                created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                modified_at   TEXT,
                created_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
                modified_by   INTEGER REFERENCES users(id) ON DELETE SET NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS priorities (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                icon        TEXT NOT NULL DEFAULT 'flag',
                color       TEXT NOT NULL DEFAULT '#6B7280' CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#'),
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                modified_at TEXT,
                created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                UNIQUE(name, project_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                description TEXT,
                icon        TEXT    NOT NULL DEFAULT 'folder',
                color       TEXT    NOT NULL DEFAULT '#3B82F6' CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#'),
                owner_id    INTEGER NOT NULL REFERENCES users(id),
                leader_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
                priority_id INTEGER REFERENCES priorities(id) ON DELETE SET NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                modified_at TEXT,
                created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_members (
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                user_id    INTEGER NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
                created_at TEXT    NOT NULL DEFAULT (datetime('now')),
                created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                PRIMARY KEY (project_id, user_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                description TEXT,
                color       TEXT    NOT NULL DEFAULT '#3B82F6' CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#'),
                project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                sort_order  INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                modified_at TEXT,
                created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id           INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                user_id            INTEGER REFERENCES users(id) ON DELETE SET NULL,
                priority_id        INTEGER REFERENCES priorities(id) ON DELETE SET NULL,
                title              TEXT    NOT NULL,
                description        TEXT,
                completed          INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0,1)),
                estimated_duration REAL,
                estimated_start    TEXT,
                estimated_end      TEXT,
                actual_start       TEXT,
                actual_end         TEXT,
                sort_order         INTEGER NOT NULL DEFAULT 0,
                created_at         TEXT    NOT NULL DEFAULT (datetime('now')),
                modified_at        TEXT,
                created_by         INTEGER REFERENCES users(id) ON DELETE SET NULL,
                modified_by        INTEGER REFERENCES users(id) ON DELETE SET NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS todo_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                title       TEXT    NOT NULL,
                completed   INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0,1)),
                sort_order  INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                modified_at TEXT,
                created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                color       TEXT NOT NULL DEFAULT '#6B7280' CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#'),
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                modified_at TEXT,
                created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                UNIQUE(name, project_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_tags (
                task_id    INTEGER NOT NULL REFERENCES tasks(id)  ON DELETE CASCADE,
                tag_id     INTEGER NOT NULL REFERENCES tags(id)   ON DELETE CASCADE,
                created_at TEXT    NOT NULL DEFAULT (datetime('now')),
                created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                PRIMARY KEY (task_id, tag_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS group_tags (
                group_id   INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                tag_id     INTEGER NOT NULL REFERENCES tags(id)   ON DELETE CASCADE,
                created_at TEXT    NOT NULL DEFAULT (datetime('now')),
                created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                PRIMARY KEY (group_id, tag_id)
            )
        """)
        _migrate(conn)
        conn.commit()
    seed_db()


def _migrate(conn: sqlite3.Connection) -> None:
    """Actualiza esquemas existentes sin romper bases de datos antiguas."""
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    # ── resources → users ────────────────────────────────────────────────────
    # SQLite 3.26+ actualiza automáticamente las FK en otras tablas al renombrar
    if "resources" in tables and "users" not in tables:
        conn.execute("ALTER TABLE resources RENAME TO users")
        tables.add("users")
        tables.discard("resources")

    # Drop legacy resources table if it still exists alongside users
    if "resources" in tables:
        conn.execute("DROP TABLE IF EXISTS resources")
        tables.discard("resources")

    if "users" in tables:
        ucols = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
        for col, typedef in [
            ("password_hash", "TEXT NOT NULL DEFAULT 'changeme'"),
            ("is_admin",      "INTEGER NOT NULL DEFAULT 0"),
            ("modified_at",   "TEXT"),
            ("created_by",    "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
            ("modified_by",   "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ]:
            if col not in ucols:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} {typedef}")
        # If no admins exist yet, promote the first registered user
        if conn.execute("SELECT COUNT(*) FROM users WHERE is_admin=1").fetchone()[0] == 0:
            conn.execute(
                "UPDATE users SET is_admin=1 WHERE id=(SELECT MIN(id) FROM users)"
            )
        # Rebuild users if is_admin CHECK constraint is missing
        _u_sql = (conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone() or [""])[0]
        if "CHECK(is_admin IN (0,1))" not in _u_sql:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("DROP TABLE IF EXISTS users_new")
            conn.execute("""
                CREATE TABLE users_new (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    name          TEXT    NOT NULL,
                    email         TEXT    NOT NULL UNIQUE,
                    password_hash TEXT    NOT NULL,
                    avatar_url    TEXT,
                    is_admin      INTEGER NOT NULL DEFAULT 0 CHECK(is_admin IN (0,1)),
                    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                    modified_at   TEXT,
                    created_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by   INTEGER REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            conn.execute("""
                INSERT INTO users_new
                    (id, name, email, password_hash, avatar_url, is_admin,
                     created_at, modified_at, created_by, modified_by)
                SELECT id, name, email, password_hash, avatar_url, is_admin,
                       created_at, modified_at, created_by, modified_by
                FROM users
            """)
            conn.execute("DROP TABLE users")
            conn.execute("ALTER TABLE users_new RENAME TO users")
            conn.execute("PRAGMA foreign_keys = ON")

    # ── project_members ───────────────────────────────────────────────────────
    # (creada por CREATE TABLE IF NOT EXISTS arriba si es BD nueva)

    # ── projects: fix stale FK leader_id → resources (rename didn't update it) ─
    if "projects" in tables:
        proj_fk_tables = {r["table"] for r in conn.execute("PRAGMA foreign_key_list(projects)")}
        if "resources" in proj_fk_tables:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("DROP TABLE IF EXISTS projects_new")
            conn.execute("""
                CREATE TABLE projects_new (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT    NOT NULL,
                    description TEXT,
                    icon        TEXT    NOT NULL DEFAULT 'folder',
                    color       TEXT    NOT NULL DEFAULT '#3B82F6',
                    owner_id    INTEGER REFERENCES users(id),
                    leader_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    priority_id INTEGER REFERENCES priorities(id) ON DELETE SET NULL,
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                    modified_at TEXT,
                    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            conn.execute("""
                INSERT INTO projects_new
                    (id, name, description, icon, color, owner_id, leader_id, priority_id,
                     created_at, modified_at, created_by, modified_by)
                SELECT id, name, description, icon, color, owner_id, leader_id, priority_id,
                       created_at, modified_at, created_by, modified_by
                FROM projects
            """)
            conn.execute("DROP TABLE projects")
            conn.execute("ALTER TABLE projects_new RENAME TO projects")
            conn.execute("PRAGMA foreign_keys = ON")
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    # ── projects: owner_id + audit ────────────────────────────────────────────
    if "projects" in tables:
        pcols = {r[1] for r in conn.execute("PRAGMA table_info(projects)")}
        if "owner_id" not in pcols:
            conn.execute(
                "ALTER TABLE projects ADD COLUMN owner_id INTEGER REFERENCES users(id)"
            )
            # Asignar owner = leader si existe, si no el primer usuario
            conn.execute("""
                UPDATE projects
                SET owner_id = COALESCE(
                    leader_id,
                    (SELECT id FROM users ORDER BY id LIMIT 1)
                )
            """)
        for col, typedef in [
            ("modified_at", "TEXT"),
            ("created_by",  "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
            ("modified_by", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ]:
            if col not in pcols:
                conn.execute(f"ALTER TABLE projects ADD COLUMN {col} {typedef}")

    # ── groups: project_id CASCADE + audit ───────────────────────────────────
    if "groups" in tables:
        gcols = {r[1] for r in conn.execute("PRAGMA table_info(groups)")}
        if "color" not in gcols:
            conn.execute("ALTER TABLE groups ADD COLUMN color TEXT NOT NULL DEFAULT '#3B82F6'")
        if "project_id" not in gcols:
            conn.execute(
                "ALTER TABLE groups ADD COLUMN project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE"
            )
        for col, typedef in [
            ("modified_at", "TEXT"),
            ("created_by",  "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
            ("modified_by", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ]:
            if col not in gcols:
                conn.execute(f"ALTER TABLE groups ADD COLUMN {col} {typedef}")
        # Rebuild groups if project_id FK is not CASCADE, not NOT NULL, or color CHECK missing
        _g_sql = (conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='groups'"
        ).fetchone() or [""])[0]
        group_notnull = {r["name"]: r["notnull"] for r in conn.execute("PRAGMA table_info(groups)")}
        group_fk_actions = {
            r["from"]: r["on_delete"]
            for r in conn.execute("PRAGMA foreign_key_list(groups)")
        }
        if (group_fk_actions.get("project_id") != "CASCADE"
                or not group_notnull.get("project_id", 0)
                or "CHECK(LENGTH(color)" not in _g_sql):
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("DROP TABLE IF EXISTS groups_new")
            conn.execute("""
                CREATE TABLE groups_new (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT    NOT NULL,
                    description TEXT,
                    color       TEXT    NOT NULL DEFAULT '#3B82F6' CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#'),
                    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                    modified_at TEXT,
                    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            conn.execute("""
                INSERT INTO groups_new
                    (id, name, description, color, project_id,
                     created_at, modified_at, created_by, modified_by)
                SELECT id, name, description, color, project_id,
                       created_at, modified_at, created_by, modified_by
                FROM groups
            """)
            conn.execute("DROP TABLE groups")
            conn.execute("ALTER TABLE groups_new RENAME TO groups")
            conn.execute("PRAGMA foreign_keys = ON")

        # Add sort_order column if missing
        gcols = {r[1] for r in conn.execute("PRAGMA table_info(groups)")}
        if "sort_order" not in gcols:
            conn.execute("ALTER TABLE groups ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
            conn.execute("""
                UPDATE groups SET sort_order = (
                    SELECT COUNT(*) FROM groups g2
                    WHERE g2.project_id = groups.project_id AND g2.id < groups.id
                )
            """)

    # ── tasks: user_id + audit ────────────────────────────────────────────────
    if "tasks" in tables:
        tcols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
        for col, typedef in [
            ("estimated_duration", "REAL"),
            ("estimated_start",    "TEXT"),
            ("estimated_end",      "TEXT"),
            ("actual_start",       "TEXT"),
            ("actual_end",         "TEXT"),
        ]:
            if col not in tcols:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {typedef}")

        if "user_id" not in tcols:
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL"
            )
            # resource_id values don't map to user IDs — leave user_id as NULL

        if "priority_id" not in tcols:
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN priority_id INTEGER REFERENCES priorities(id) ON DELETE SET NULL"
            )

        for col, typedef in [
            ("modified_at", "TEXT"),
            ("created_by",  "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
            ("modified_by", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ]:
            if col not in tcols:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {typedef}")

        # Remove legacy resource_id column (requires table rebuild in SQLite)
        tcols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
        if "resource_id" in tcols:
            conn.execute("DROP TABLE IF EXISTS tasks_new")
            conn.execute("""
                CREATE TABLE tasks_new (
                    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id           INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                    user_id            INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    priority_id        INTEGER REFERENCES priorities(id) ON DELETE SET NULL,
                    title              TEXT    NOT NULL,
                    description        TEXT,
                    completed          INTEGER NOT NULL DEFAULT 0,
                    estimated_duration REAL,
                    estimated_start    TEXT,
                    estimated_end      TEXT,
                    actual_start       TEXT,
                    actual_end         TEXT,
                    created_at         TEXT    NOT NULL DEFAULT (datetime('now')),
                    modified_at        TEXT,
                    created_by         INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by        INTEGER REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            conn.execute("""
                INSERT INTO tasks_new
                    (id, group_id, user_id, priority_id, title, description,
                     completed, estimated_duration, estimated_start, estimated_end,
                     actual_start, actual_end, created_at, modified_at, created_by, modified_by)
                SELECT id, group_id, user_id, priority_id, title, description,
                       completed, estimated_duration, estimated_start, estimated_end,
                       actual_start, actual_end, created_at, modified_at, created_by, modified_by
                FROM tasks
            """)
            conn.execute("DROP TABLE tasks")
            conn.execute("ALTER TABLE tasks_new RENAME TO tasks")

        # Rebuild tasks if completed CHECK is missing
        _t_sql = (conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='tasks'"
        ).fetchone() or [""])[0]
        if "CHECK(completed IN (0,1))" not in _t_sql:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("DROP TABLE IF EXISTS tasks_new")
            conn.execute("""
                CREATE TABLE tasks_new (
                    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id           INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                    user_id            INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    priority_id        INTEGER REFERENCES priorities(id) ON DELETE SET NULL,
                    title              TEXT    NOT NULL,
                    description        TEXT,
                    completed          INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0,1)),
                    estimated_duration REAL,
                    estimated_start    TEXT,
                    estimated_end      TEXT,
                    actual_start       TEXT,
                    actual_end         TEXT,
                    created_at         TEXT    NOT NULL DEFAULT (datetime('now')),
                    modified_at        TEXT,
                    created_by         INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by        INTEGER REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            conn.execute("""
                INSERT INTO tasks_new
                    (id, group_id, user_id, priority_id, title, description,
                     completed, estimated_duration, estimated_start, estimated_end,
                     actual_start, actual_end, created_at, modified_at, created_by, modified_by)
                SELECT id, group_id, user_id, priority_id, title, description,
                       completed, estimated_duration, estimated_start, estimated_end,
                       actual_start, actual_end, created_at, modified_at, created_by, modified_by
                FROM tasks
            """)
            conn.execute("DROP TABLE tasks")
            conn.execute("ALTER TABLE tasks_new RENAME TO tasks")
            conn.execute("PRAGMA foreign_keys = ON")

        # Add sort_order column if missing (safe with ALTER TABLE + DEFAULT 0)
        tcols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
        if "sort_order" not in tcols:
            conn.execute("ALTER TABLE tasks ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
            conn.execute("""
                UPDATE tasks SET sort_order = (
                    SELECT COUNT(*) FROM tasks t2
                    WHERE t2.group_id = tasks.group_id AND t2.id < tasks.id
                )
            """)

    # ── todo_items: audit ─────────────────────────────────────────────────────
    if "todo_items" in tables:
        tdicols = {r[1] for r in conn.execute("PRAGMA table_info(todo_items)")}
        for col, typedef in [
            ("created_at",  "TEXT"),   # NOT NULL DEFAULT (datetime('now')) invalid for ALTER TABLE
            ("modified_at", "TEXT"),
            ("created_by",  "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
            ("modified_by", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ]:
            if col not in tdicols:
                conn.execute(f"ALTER TABLE todo_items ADD COLUMN {col} {typedef}")
        # Rebuild todo_items if completed CHECK is missing
        _tdi_sql = (conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='todo_items'"
        ).fetchone() or [""])[0]
        if "CHECK(completed IN (0,1))" not in _tdi_sql:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("DROP TABLE IF EXISTS todo_items_new")
            conn.execute("""
                CREATE TABLE todo_items_new (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    title       TEXT    NOT NULL,
                    completed   INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0,1)),
                    sort_order  INTEGER NOT NULL DEFAULT 0,
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                    modified_at TEXT,
                    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            conn.execute("""
                INSERT INTO todo_items_new
                    (id, task_id, title, completed, sort_order,
                     created_at, modified_at, created_by, modified_by)
                SELECT id, task_id, title, completed, sort_order,
                       COALESCE(created_at, datetime('now')),
                       modified_at, created_by, modified_by
                FROM todo_items
            """)
            conn.execute("DROP TABLE todo_items")
            conn.execute("ALTER TABLE todo_items_new RENAME TO todo_items")
            conn.execute("PRAGMA foreign_keys = ON")

    # ── tags: project_id + audit ──────────────────────────────────────────────
    if "tags" in tables:
        tagcols = {r[1] for r in conn.execute("PRAGMA table_info(tags)")}
        if "project_id" not in tagcols:
            # Rebuild table to add project_id and change UNIQUE constraint
            conn.execute("DROP TABLE IF EXISTS tags_new")
            conn.execute("""
                CREATE TABLE tags_new (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL,
                    project_id  INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                    color       TEXT NOT NULL DEFAULT '#6B7280',
                    created_at  TEXT,
                    modified_at TEXT,
                    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    UNIQUE(name, project_id)
                )
            """)
            conn.execute("""
                INSERT INTO tags_new (id, name, color, created_at, modified_at, created_by, modified_by)
                SELECT id, name, color, created_at, modified_at, created_by, modified_by FROM tags
            """)
            conn.execute("DROP TABLE tags")
            conn.execute("ALTER TABLE tags_new RENAME TO tags")
            tagcols = {r[1] for r in conn.execute("PRAGMA table_info(tags)")}
        for col, typedef in [
            ("created_at",  "TEXT"),
            ("modified_at", "TEXT"),
            ("created_by",  "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
            ("modified_by", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ]:
            if col not in tagcols:
                conn.execute(f"ALTER TABLE tags ADD COLUMN {col} {typedef}")
        # Rebuild tags if project_id is nullable or color CHECK is missing
        _tag_sql = (conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='tags'"
        ).fetchone() or [""])[0]
        _tag_notnull = {r["name"]: r["notnull"] for r in conn.execute("PRAGMA table_info(tags)")}
        if not _tag_notnull.get("project_id", 0) or "CHECK(LENGTH(color)" not in _tag_sql:
            conn.execute("DELETE FROM tags WHERE project_id IS NULL")
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("DROP TABLE IF EXISTS tags_new")
            conn.execute("""
                CREATE TABLE tags_new (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL,
                    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    color       TEXT NOT NULL DEFAULT '#6B7280' CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#'),
                    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                    modified_at TEXT,
                    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    UNIQUE(name, project_id)
                )
            """)
            conn.execute("""
                INSERT INTO tags_new
                    (id, name, project_id, color, created_at, modified_at, created_by, modified_by)
                SELECT id, name, project_id, color,
                       COALESCE(created_at, datetime('now')),
                       modified_at, created_by, modified_by
                FROM tags
            """)
            conn.execute("DROP TABLE tags")
            conn.execute("ALTER TABLE tags_new RENAME TO tags")
            conn.execute("PRAGMA foreign_keys = ON")

    # ── priorities: project_id + audit ───────────────────────────────────────
    if "priorities" in tables:
        pricols = {r[1] for r in conn.execute("PRAGMA table_info(priorities)")}
        if "project_id" not in pricols:
            # Rebuild table to add project_id and change UNIQUE constraint
            conn.execute("DROP TABLE IF EXISTS priorities_new")
            conn.execute("""
                CREATE TABLE priorities_new (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL,
                    project_id  INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                    icon        TEXT NOT NULL DEFAULT 'flag',
                    color       TEXT NOT NULL DEFAULT '#6B7280',
                    created_at  TEXT,
                    modified_at TEXT,
                    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    UNIQUE(name, project_id)
                )
            """)
            conn.execute("""
                INSERT INTO priorities_new (id, name, icon, color, created_at, modified_at, created_by, modified_by)
                SELECT id, name, icon, color, created_at, modified_at, created_by, modified_by FROM priorities
            """)
            conn.execute("DROP TABLE priorities")
            conn.execute("ALTER TABLE priorities_new RENAME TO priorities")
            pricols = {r[1] for r in conn.execute("PRAGMA table_info(priorities)")}
        for col, typedef in [
            ("created_at",  "TEXT"),
            ("modified_at", "TEXT"),
            ("created_by",  "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
            ("modified_by", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ]:
            if col not in pricols:
                conn.execute(f"ALTER TABLE priorities ADD COLUMN {col} {typedef}")
        # Rebuild priorities if project_id is nullable or color CHECK is missing
        _pri_sql = (conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='priorities'"
        ).fetchone() or [""])[0]
        _pri_notnull = {r["name"]: r["notnull"] for r in conn.execute("PRAGMA table_info(priorities)")}
        if not _pri_notnull.get("project_id", 0) or "CHECK(LENGTH(color)" not in _pri_sql:
            conn.execute("DELETE FROM priorities WHERE project_id IS NULL")
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("DROP TABLE IF EXISTS priorities_new")
            conn.execute("""
                CREATE TABLE priorities_new (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL,
                    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    icon        TEXT NOT NULL DEFAULT 'flag',
                    color       TEXT NOT NULL DEFAULT '#6B7280' CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#'),
                    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                    modified_at TEXT,
                    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    UNIQUE(name, project_id)
                )
            """)
            conn.execute("""
                INSERT INTO priorities_new
                    (id, name, project_id, icon, color, created_at, modified_at, created_by, modified_by)
                SELECT id, name, project_id, icon, color,
                       COALESCE(created_at, datetime('now')),
                       modified_at, created_by, modified_by
                FROM priorities
            """)
            conn.execute("DROP TABLE priorities")
            conn.execute("ALTER TABLE priorities_new RENAME TO priorities")
            conn.execute("PRAGMA foreign_keys = ON")

    # ── task_tags: audit columns ─────────────────────────────────────────────
    if "task_tags" in tables:
        ttcols = {r[1] for r in conn.execute("PRAGMA table_info(task_tags)")}
        for col, typedef in [
            ("created_at", "TEXT"),
            ("created_by", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ]:
            if col not in ttcols:
                conn.execute(f"ALTER TABLE task_tags ADD COLUMN {col} {typedef}")

    # ── group_tags: audit columns ────────────────────────────────────────────
    if "group_tags" in tables:
        gtcols = {r[1] for r in conn.execute("PRAGMA table_info(group_tags)")}
        for col, typedef in [
            ("created_at", "TEXT"),
            ("created_by", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ]:
            if col not in gtcols:
                conn.execute(f"ALTER TABLE group_tags ADD COLUMN {col} {typedef}")

    # ── data cleanup ─────────────────────────────────────────────────────────
    # Orphan groups (project_id=NULL from old SET NULL behaviour) — delete them
    conn.execute("DELETE FROM groups WHERE project_id IS NULL")
    # Projects with owner_id=NULL — assign to first registered user
    conn.execute("""
        UPDATE projects SET owner_id = (SELECT MIN(id) FROM users)
        WHERE owner_id IS NULL AND (SELECT COUNT(*) FROM users) > 0
    """)
    # Legacy priorities without a project (pre-scoping era) — delete if unused
    conn.execute("""
        DELETE FROM priorities
        WHERE project_id IS NULL
          AND id NOT IN (SELECT DISTINCT priority_id FROM tasks WHERE priority_id IS NOT NULL)
          AND id NOT IN (SELECT DISTINCT priority_id FROM projects WHERE priority_id IS NOT NULL)
    """)

    # ── projects: owner_id NOT NULL + color CHECK ─────────────────────────────
    # Must run after data cleanup (owner_id NULLs already fixed above)
    if "projects" in tables:
        _proj_sql = (conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='projects'"
        ).fetchone() or [""])[0]
        _proj_notnull = {r["name"]: r["notnull"] for r in conn.execute("PRAGMA table_info(projects)")}
        if not _proj_notnull.get("owner_id", 0) or "CHECK(LENGTH(color)" not in _proj_sql:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("DROP TABLE IF EXISTS projects_new")
            conn.execute("""
                CREATE TABLE projects_new (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT    NOT NULL,
                    description TEXT,
                    icon        TEXT    NOT NULL DEFAULT 'folder',
                    color       TEXT    NOT NULL DEFAULT '#3B82F6' CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#'),
                    owner_id    INTEGER NOT NULL REFERENCES users(id),
                    leader_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    priority_id INTEGER REFERENCES priorities(id) ON DELETE SET NULL,
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                    modified_at TEXT,
                    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            conn.execute("""
                INSERT INTO projects_new
                    (id, name, description, icon, color, owner_id, leader_id, priority_id,
                     created_at, modified_at, created_by, modified_by)
                SELECT id, name, description, icon, color, owner_id, leader_id, priority_id,
                       created_at, modified_at, created_by, modified_by
                FROM projects
            """)
            conn.execute("DROP TABLE projects")
            conn.execute("ALTER TABLE projects_new RENAME TO projects")
            conn.execute("PRAGMA foreign_keys = ON")

    # ── legacy tables ─────────────────────────────────────────────────────────
    for legacy_table in ("task_resources",):
        if legacy_table in tables:
            conn.execute(f"DROP TABLE {legacy_table}")


def seed_db() -> None:
    with get_connection() as conn:
        # Skip seed if any data already exists
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return

        # ── Usuarios ──────────────────────────────────────────────────────────
        u_alice = conn.execute(
            "INSERT INTO users (name, email, password_hash, avatar_url, is_admin) VALUES (?,?,?,?,1)",
            ("Alice Martín", "alice@example.com", "pbkdf2$seed$placeholder", "https://i.pravatar.cc/40?img=1"),
        ).lastrowid
        u_bob = conn.execute(
            "INSERT INTO users (name, email, password_hash, avatar_url) VALUES (?,?,?,?)",
            ("Bob Chen", "bob@example.com", "pbkdf2$seed$placeholder", "https://i.pravatar.cc/40?img=3"),
        ).lastrowid
        u_carol = conn.execute(
            "INSERT INTO users (name, email, password_hash, avatar_url) VALUES (?,?,?,?)",
            ("Carol López", "carol@example.com", "pbkdf2$seed$placeholder", "https://i.pravatar.cc/40?img=5"),
        ).lastrowid

        # ── Proyecto por defecto (sin priority_id aún — las prioridades son
        #    project-scoped, así que se crean después del proyecto) ──────────
        proj_default = conn.execute(
            """INSERT INTO projects (name, description, icon, color, owner_id, leader_id)
               VALUES (?,?,?,?,?,?)""",
            ("Proyecto Principal", "Tablero de tareas general del equipo",
             "rocket_launch", "#3B82F6", u_alice, u_alice),
        ).lastrowid

        # Añadir miembros al proyecto
        conn.executemany(
            "INSERT INTO project_members (project_id, user_id) VALUES (?,?)",
            [(proj_default, u_bob), (proj_default, u_carol)],
        )

        # ── Prioridades (scoped to default project) ──────────────────────────
        p_critical = conn.execute(
            "INSERT INTO priorities (name, icon, color, project_id) VALUES (?,?,?,?)",
            ("Critical", "emergency", "#EF4444", proj_default),
        ).lastrowid
        p_high = conn.execute(
            "INSERT INTO priorities (name, icon, color, project_id) VALUES (?,?,?,?)",
            ("High", "arrow_upward", "#F97316", proj_default),
        ).lastrowid
        p_normal = conn.execute(
            "INSERT INTO priorities (name, icon, color, project_id) VALUES (?,?,?,?)",
            ("Normal", "remove", "#3B82F6", proj_default),
        ).lastrowid
        p_low = conn.execute(
            "INSERT INTO priorities (name, icon, color, project_id) VALUES (?,?,?,?)",
            ("Low", "arrow_downward", "#6B7280", proj_default),
        ).lastrowid

        # Asignar la prioridad Normal al proyecto ahora que existe
        conn.execute("UPDATE projects SET priority_id=? WHERE id=?", (p_normal, proj_default))

        # ── Grupos ────────────────────────────────────────────────────────────
        g_backlog = conn.execute(
            "INSERT INTO groups (name, description, color, project_id) VALUES (?,?,?,?)",
            ("Backlog", "Tareas pendientes de planificación", "#6B7280", proj_default),
        ).lastrowid
        g_progress = conn.execute(
            "INSERT INTO groups (name, description, color, project_id) VALUES (?,?,?,?)",
            ("En Progreso", "Tareas actualmente en desarrollo", "#F59E0B", proj_default),
        ).lastrowid
        g_review = conn.execute(
            "INSERT INTO groups (name, description, color, project_id) VALUES (?,?,?,?)",
            ("En Revisión", "Pendiente de revisión y QA", "#8B5CF6", proj_default),
        ).lastrowid
        g_done = conn.execute(
            "INSERT INTO groups (name, description, color, project_id) VALUES (?,?,?,?)",
            ("Completado", "Tareas finalizadas y entregadas", "#10B981", proj_default),
        ).lastrowid

        # ── Tags (scoped to default project) ─────────────────────────────────
        t_backend  = conn.execute("INSERT INTO tags (name, color, project_id) VALUES (?,?,?)", ("Backend",       "#3B82F6", proj_default)).lastrowid
        t_frontend = conn.execute("INSERT INTO tags (name, color, project_id) VALUES (?,?,?)", ("Frontend",      "#F97316", proj_default)).lastrowid
        t_urgent   = conn.execute("INSERT INTO tags (name, color, project_id) VALUES (?,?,?)", ("Urgente",       "#EF4444", proj_default)).lastrowid
        t_docs     = conn.execute("INSERT INTO tags (name, color, project_id) VALUES (?,?,?)", ("Documentación", "#8B5CF6", proj_default)).lastrowid
        t_debt     = conn.execute("INSERT INTO tags (name, color, project_id) VALUES (?,?,?)", ("Deuda técnica", "#6B7280", proj_default)).lastrowid

        # ── Tareas ────────────────────────────────────────────────────────────
        tasks_data = [
            (g_backlog,  u_carol, p_normal,   "Diseñar wireframes del dashboard",
             "Crear wireframes de baja fidelidad para las vistas principales",
             0, 4.0, "2024-02-05T09:00:00", "2024-02-09T18:00:00", None, None),
            (g_backlog,  u_bob,   p_high,     "Escribir tests de integración",
             "Cobertura de los endpoints críticos con pytest y TestClient",
             0, 6.0, "2024-02-12T09:00:00", "2024-02-14T18:00:00", None, None),
            (g_backlog,  u_alice, p_low,      "Documentar API con OpenAPI",
             "Revisar y completar descripciones de todos los endpoints",
             0, 2.0, None, None, None, None),
            (g_progress, u_bob,   p_critical, "Implementar autenticación JWT",
             "Login, refresh token y middleware de autenticación",
             0, 8.0, "2024-01-22T09:00:00", "2024-01-29T18:00:00", "2024-01-23T09:00:00", None),
            (g_progress, u_alice, p_high,     "Refactorizar módulo de notificaciones",
             "Extraer lógica de envío a un servicio independiente",
             0, 5.0, "2024-01-24T09:00:00", "2024-01-28T18:00:00", "2024-01-24T10:00:00", None),
            (g_review,   u_carol, p_normal,   "Revisar paleta de colores y tipografía",
             "Validar contraste WCAG AA en todos los componentes",
             0, 2.0, "2024-01-18T09:00:00", "2024-01-19T18:00:00", "2024-01-18T09:00:00", None),
            (g_review,   u_alice, p_high,     "Code review módulo de pagos",
             "Revisar integración con Stripe y manejo de errores",
             0, 3.0, None, None, "2024-01-20T09:00:00", None),
            (g_done,     u_bob,   p_normal,   "Configurar entorno de desarrollo",
             "Docker Compose con PostgreSQL, Redis y hot-reload",
             1, 2.0, "2024-01-10T09:00:00", "2024-01-11T18:00:00", "2024-01-10T09:00:00", "2024-01-11T16:30:00"),
            (g_done,     u_alice, p_low,      "Definir arquitectura del sistema",
             "ADR con decisiones sobre Clean Architecture y stack tecnológico",
             1, 4.0, "2024-01-08T09:00:00", "2024-01-09T18:00:00", "2024-01-08T09:00:00", "2024-01-09T17:00:00"),
        ]

        task_ids = []
        for t in tasks_data:
            tid = conn.execute(
                """INSERT INTO tasks
                       (group_id, user_id, priority_id, title, description, completed,
                        estimated_duration, estimated_start, estimated_end, actual_start, actual_end)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                t,
            ).lastrowid
            task_ids.append(tid)

        # ── Task Tags ─────────────────────────────────────────────────────────
        conn.executemany(
            "INSERT INTO task_tags (task_id, tag_id) VALUES (?,?)",
            [
                (task_ids[0], t_frontend),
                (task_ids[1], t_backend), (task_ids[1], t_debt),
                (task_ids[2], t_docs),
                (task_ids[3], t_backend), (task_ids[3], t_urgent),
                (task_ids[4], t_backend), (task_ids[4], t_debt),
                (task_ids[5], t_frontend), (task_ids[5], t_docs),
                (task_ids[6], t_backend),
                (task_ids[8], t_docs),
            ],
        )

        conn.executemany(
            "INSERT INTO group_tags (group_id, tag_id) VALUES (?,?)",
            [(g_backlog, t_debt), (g_progress, t_urgent), (g_review, t_docs)],
        )

        # ── Todo Items ────────────────────────────────────────────────────────
        conn.executemany(
            "INSERT INTO todo_items (task_id, title, completed, sort_order) VALUES (?,?,?,?)",
            [
                (task_ids[3], "Crear modelo User y migración de BD",  1, 0),
                (task_ids[3], "Implementar endpoint /auth/login",      1, 1),
                (task_ids[3], "Añadir middleware de validación",       0, 2),
                (task_ids[4], "Extraer servicio EmailService",  0, 0),
                (task_ids[4], "Añadir tests unitarios",         0, 1),
                (task_ids[4], "Documentar la interfaz pública", 1, 2),
                (task_ids[0], "Vista de lista de tareas",   0, 0),
                (task_ids[0], "Vista de detalle de tarea",  0, 1),
                (task_ids[0], "Flujo de creación de tarea", 0, 2),
                (task_ids[7], "Crear docker-compose.yml",        1, 0),
                (task_ids[7], "Configurar variables de entorno", 1, 1),
            ],
        )
        conn.commit()
