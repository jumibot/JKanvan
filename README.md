# JKanban

Aplicación de gestión de tareas estilo Kanban con soporte multiproyecto, equipos y prioridades personalizadas.

## Funcionalidades

### Proyectos
- Crear y gestionar múltiples proyectos con nombre, icono, color y descripción
- Asignar un **Team Leader** y una **prioridad** a cada proyecto
- Vista de progreso por proyecto (tareas completadas / total)

### Tablero Kanban
- Grupos de tareas (columnas) con color propio y ordenación por drag & drop
- Reordenación de columnas arrastrando la cabecera
- Reordenación de tareas dentro de una columna y movimiento entre columnas

### Tareas
- Crear, editar y eliminar tareas
- Campos: título, descripción, responsable, duración estimada, fecha de inicio y fin
- **Etiquetas** multiselección con colores personalizados por proyecto
- **Prioridad** por tarea con icono y color
- **Subtareas** (checklist) con progreso visual
- Marcar tareas como completadas

### Etiquetas y Prioridades
- Gestionadas por proyecto (owner o team leader)
- Paleta de colores y selector de iconos para prioridades

### Equipo
- Asignar y eliminar miembros por proyecto
- Vista de roles: Owner, Líder, Miembros
- Panel de administración de usuarios (solo admins)

### Autenticación
- Registro e inicio de sesión con JWT
- Sesión persistida en `localStorage`
- Roles: usuario estándar y administrador

---

## Tecnologías

### Backend
| Tecnología | Uso |
|---|---|
| **Python 3.13** | Lenguaje principal |
| **FastAPI** | Framework REST API |
| **SQLite** | Base de datos (fichero `tasks.db`) |
| **PyJWT** | Autenticación con tokens JWT |
| **Uvicorn** | Servidor ASGI |
| **pytest + httpx** | Suite de tests (293 tests) |

### Frontend
| Tecnología | Uso |
|---|---|
| **HTML5 / Vanilla JS** | SPA sin framework ni bundler |
| **Tailwind CSS** (CDN) | Utilidades de estilo |
| **Material Symbols** | Iconografía |
| **Drag & Drop API** | Reordenación de tareas y columnas |

El frontend se sirve directamente desde el backend a través de `StaticFiles` de FastAPI.

---

## Estructura del repositorio

```
jkanban/
│
├── backend/                        # API REST (FastAPI)
│   ├── main.py                     # Punto de entrada, montaje de rutas y frontend
│   ├── requirements.txt            # Dependencias Python
│   │
│   ├── domain/                     # Capa de dominio (entidades y contratos)
│   │   ├── entities.py             # Dataclasses: Project, Group, Task, Tag, Priority, User, Todo
│   │   ├── repositories.py         # Interfaces abstractas de repositorio
│   │   └── exceptions.py           # Excepciones de negocio
│   │
│   ├── application/                # Casos de uso
│   │   ├── project_use_cases.py
│   │   ├── group_use_cases.py
│   │   ├── task_use_cases.py
│   │   ├── tag_use_cases.py
│   │   ├── priority_use_cases.py
│   │   ├── user_use_cases.py
│   │   ├── todo_use_cases.py
│   │   └── resource_use_cases.py   # Miembros de proyecto
│   │
│   ├── infrastructure/             # Implementaciones concretas
│   │   ├── database.py             # Conexión SQLite y creación de tablas
│   │   ├── jwt_handler.py          # Generación y validación de tokens
│   │   └── repositories/           # Implementaciones SQLite de cada repositorio
│   │
│   └── interfaces/                 # Capa HTTP (FastAPI)
│       ├── schemas.py              # Modelos Pydantic (request / response)
│       ├── dependencies.py         # Inyección de dependencias (auth, DB)
│       └── routers/                # Un router por entidad
│           ├── auth.py
│           ├── projects.py
│           ├── groups.py
│           ├── tasks.py
│           ├── tags.py
│           ├── priorities.py
│           ├── users.py
│           ├── todos.py
│           ├── resources.py
│           └── admin.py
│
├── frontend/                       # SPA (Vanilla JS + Tailwind)
│   ├── index.html                  # HTML, estilos CSS y bloque init
│   └── js/
│       ├── state.js                # Estado global S
│       ├── utils.js                # esc, avatar, toast, hashCol
│       ├── api.js                  # Capa HTTP: req, GET/POST/PATCH/DEL, loadAll
│       ├── auth.js                 # Login, registro, logout, auth wall
│       ├── router.js               # go, route, hashchange
│       ├── render.js               # renderSidebar, renderHeader, renderContent
│       ├── delete.js               # confirmDel, confirmCascadeDelProject
│       ├── dnd.js                  # Drag & drop de tareas y columnas
│       ├── views/
│       │   ├── dashboard.js        # Vista de proyectos
│       │   ├── board.js            # Tablero Kanban
│       │   ├── tags.js             # Vista de etiquetas del proyecto
│       │   ├── priorities.js       # Vista de prioridades del proyecto
│       │   └── team.js             # Vista de equipo / admin de usuarios
│       └── modals/
│           ├── base.js             # showModal, closeM, mhdr, mfoot, swatches
│           ├── project.js          # Modal proyecto y menú contextual
│           ├── group.js            # Modal grupo de tareas
│           ├── task.js             # Modal tarea (etiquetas, prioridad inline)
│           ├── subtask.js          # Subtareas: add, toggle, delete
│           ├── tag.js              # Modal etiqueta
│           ├── priority.js         # Modal prioridad
│           └── user.js             # Modales de usuario y perfil
│
├── tests/                          # 293 tests de integración (pytest)
│   ├── conftest.py                 # Fixtures: client, auth, admin_auth
│   ├── test_auth.py
│   ├── test_projects.py
│   ├── test_groups.py
│   ├── test_tasks.py
│   ├── test_tags.py
│   ├── test_priorities.py
│   ├── test_users.py
│   ├── test_todos.py
│   └── test_admin.py
│
├── scripts/
│   └── start-dev.ps1               # Arranca Uvicorn con virtualenv automático
│
└── docs/
    └── screens/                    # Referencias visuales de diseño
```

---

## Arranque en desarrollo

```powershell
# Instalar dependencias
pip install -r backend/requirements.txt

# Arrancar el servidor (puerto por defecto: 8000)
.\scripts\start-dev.ps1

# O directamente con uvicorn
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

La aplicación queda disponible en `http://127.0.0.1:8000`.

## Tests

```bash
pytest tests/
```
