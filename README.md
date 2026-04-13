# JKanban

JKanban es una aplicación web de gestión de tareas estilo Kanban diseñada para equipos que trabajan con múltiples proyectos en paralelo. Permite organizar el trabajo en tableros visuales con grupos de tareas personalizables, asignar responsables, establecer fechas y duraciones estimadas, y clasificar las tareas mediante etiquetas y prioridades propias de cada proyecto.

La aplicación incluye gestión de equipos por proyecto —con roles de owner, líder y miembro—, subtareas con seguimiento de progreso, drag & drop para reordenar tareas y columnas, y un panel de administración de plataforma para gestionar usuarios y sus datos de forma centralizada.

El backend expone una API REST construida con FastAPI y persiste los datos en SQLite. El frontend es una SPA en Vanilla JS servida directamente por el propio backend, sin dependencias de frameworks ni proceso de build.

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

### Administración de plataforma
Funciones exclusivas para usuarios con rol **admin**:
- Crear usuarios directamente desde el panel (sin pasar por el registro público)
- Editar cualquier usuario: nombre, email, contraseña, avatar
- Promover o revocar el rol de administrador en cualquier cuenta (no en la propia)
- Eliminación en cascada de usuarios con previsualización del impacto: muestra los proyectos que serán borrados junto con el recuento de grupos, tareas, etiquetas, prioridades y miembros afectados
- La eliminación requiere confirmación con la contraseña del admin como segunda verificación
- Un admin no puede eliminarse ni revocar sus propios privilegios

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

### Nivel raíz

| Directorio / Archivo | Contenido |
|---|---|
| `backend/` | API REST — lógica de negocio, base de datos y rutas HTTP |
| `frontend/` | SPA — HTML, estilos y módulos JavaScript |
| `tests/` | Suite de 293 tests de integración (pytest) |
| `scripts/` | Scripts de utilidad para desarrollo |
| `docs/` | Referencias visuales de diseño |

---

### Backend — `backend/`

El backend sigue una **arquitectura por capas** (domain → application → infrastructure → interfaces).

| Capa | Directorio | Responsabilidad |
|---|---|---|
| Entrada | `main.py` | Punto de entrada: registra routers y sirve el frontend estático |
| Dominio | `domain/` | Entidades, interfaces de repositorio y excepciones de negocio |
| Aplicación | `application/` | Casos de uso: orquesta dominio e infraestructura |
| Infraestructura | `infrastructure/` | SQLite, JWT y repositorios concretos |
| Interfaces | `interfaces/` | Schemas Pydantic, dependencias FastAPI y routers HTTP |

**`domain/`**

| Archivo | Contenido |
|---|---|
| `entities.py` | Dataclasses: `Project`, `Group`, `Task`, `Tag`, `Priority`, `User`, `Todo` |
| `repositories.py` | Interfaces abstractas de repositorio |
| `exceptions.py` | Excepciones de negocio |

**`application/`** — un módulo de casos de uso por entidad

| Archivo | Entidad |
|---|---|
| `project_use_cases.py` | Proyectos |
| `group_use_cases.py` | Grupos de tareas |
| `task_use_cases.py` | Tareas |
| `tag_use_cases.py` | Etiquetas |
| `priority_use_cases.py` | Prioridades |
| `user_use_cases.py` | Usuarios |
| `todo_use_cases.py` | Subtareas |
| `resource_use_cases.py` | Miembros de proyecto |

**`infrastructure/`**

| Archivo | Contenido |
|---|---|
| `database.py` | Conexión SQLite y creación de tablas |
| `jwt_handler.py` | Generación y validación de tokens JWT |
| `repositories/` | Implementación SQLite de cada repositorio del dominio |

**`interfaces/routers/`** — un router por entidad

| Archivo | Endpoints |
|---|---|
| `auth.py` | Login |
| `projects.py` | CRUD proyectos, miembros, previsualización de borrado |
| `groups.py` | CRUD grupos, reordenación |
| `tasks.py` | CRUD tareas, etiquetas de tarea, reordenación |
| `tags.py` | CRUD etiquetas por proyecto |
| `priorities.py` | CRUD prioridades por proyecto |
| `users.py` | CRUD usuarios, perfil |
| `todos.py` | CRUD subtareas |
| `resources.py` | Gestión de miembros |
| `admin.py` | Previsualización y borrado en cascada de usuarios |

---

### Frontend — `frontend/`

SPA de página única sin framework ni bundler. `index.html` carga los módulos JS en orden mediante `<script src>`.

**Raíz `js/`** — foundation

| Archivo | Responsabilidad |
|---|---|
| `state.js` | Objeto global `S` con el estado de la aplicación |
| `utils.js` | Helpers: `esc`, `avatar`, `toast`, `hashCol`, `emptyState` |
| `api.js` | Capa HTTP: `req`, `GET/POST/PATCH/DEL`, `loadAll`, `loadMembers` |
| `auth.js` | Login, registro, logout, auth wall |
| `router.js` | `go`, `route`, listener `hashchange` |
| `render.js` | `renderSidebar`, `renderHeader`, `renderContent` |
| `dnd.js` | Drag & drop de tareas y reordenación de columnas |
| `delete.js` | `confirmDel`, `confirmCascadeDelProject`, `execDel` |

**`js/views/`** — vistas principales

| Archivo | Vista |
|---|---|
| `dashboard.js` | Grid de proyectos con progreso |
| `board.js` | Tablero Kanban con columnas y tarjetas |
| `tags.js` | Gestión de etiquetas del proyecto |
| `priorities.js` | Gestión de prioridades del proyecto |
| `team.js` | Equipo del proyecto y panel de administración de usuarios |

**`js/modals/`** — formularios y diálogos

| Archivo | Modales |
|---|---|
| `base.js` | `showModal`, `closeM`, `mhdr`, `mfoot`, selectores de color e icono |
| `project.js` | Crear/editar proyecto, gestión de equipo, menú contextual |
| `group.js` | Crear/editar grupo de tareas, menú contextual |
| `task.js` | Crear/editar tarea con etiquetas y prioridad inline |
| `subtask.js` | Añadir, completar y eliminar subtareas |
| `tag.js` | Crear/editar etiqueta |
| `priority.js` | Crear/editar prioridad |
| `user.js` | Crear usuario, editar perfil, edición admin, borrado en cascada |

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
