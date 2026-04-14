# Frontend — Arquitectura SPA

## Índice

- [Estructura general](#estructura-general)
- [Estado global](#estado-global-jsstatejs)
- [Capa API](#capa-api-jsapijs)
- [Router](#router-jsrouterjs)
- [Pipeline de render](#pipeline-de-render-jsrenderjs)
- [Sistema de modales](#sistema-de-modales-jsmodalsbasejs)
- [Módulos de vistas y modales](#módulos-de-vistas-y-modales)
- [Seguridad frontend](#seguridad-frontend)
- [Drag & Drop](#drag--drop-jsdndjs)

---

## Estructura general

SPA (Single-Page Application) en Vanilla JS con routing por hash. Sin bundler ni framework. Los módulos JS se cargan como `<script src>` en orden de dependencias dentro de `index.html`.

**Orden de carga de scripts:**
```
state.js → utils.js → api.js → auth.js → router.js → render.js
→ views/* → modals/* → dnd.js → delete.js → [init IIFE]
```

---

## Estado global (`js/state.js`)

Un único objeto `S` mutado directamente. Cada operación que cambia datos llama a `render()` al final.

```javascript
S = {
  projects:    [],        // ProjectResponse[] — todos los proyectos accesibles
  groups:      [],        // GroupResponse[]   — todos los grupos
  tasks:       [],        // TaskResponse[]    — todas las tareas
  users:       [],        // UserResponse[]    — todos los usuarios
  tags:        [],        // TagResponse[]     — etiquetas del proyecto actual
  priorities:  [],        // PriorityResponse[]— prioridades del proyecto actual
  members:     [],        // UserResponse[]    — miembros del proyecto actual
  view:        'dashboard', // 'dashboard' | 'board' | 'team'
  pid:         null,      // int | null — project_id activo
  subview:     'kanban',  // 'kanban' | 'tags' | 'priorities' | 'team'
  currentUser: null,      // UserResponse | null
}
```

`tags`, `priorities` y `members` son project-scoped: se recargan cuando cambia `S.pid`.

---

## Capa API (`js/api.js`)

```javascript
req(method, path, body)   // fetch con token JWT; 401 → clearAuth+showAuthWall
GET(path)                 // shorthand
POST(path, body)
PATCH(path, body)
DEL(path)

loadAll()      // carga projects+groups+tasks+users en paralelo
               // si S.pid: también tags y priorities
loadMembers()  // carga S.members para el proyecto actual
```

Los errores de negocio (4xx) se propagan como `Error(body.detail)` y los modales los capturan con `toast(err.message, 'err')`.

---

## Router (`js/router.js`)

Hash-based. Se ejecuta en `hashchange` y al arrancar.

| Hash | Vista | Requiere |
|------|-------|---------|
| `#/` | Dashboard | — |
| `#/board/{pid}` | Kanban (default) | acceso al proyecto |
| `#/board/{pid}/kanban` | Kanban | acceso al proyecto |
| `#/board/{pid}/tags` | Gestión etiquetas | acceso al proyecto |
| `#/board/{pid}/priorities` | Gestión prioridades | acceso al proyecto |
| `#/board/{pid}/team` | Equipo del proyecto | acceso al proyecto |
| `#/team` | Panel admin usuarios | `is_admin` |

Al cambiar de proyecto (`newPid !== S.pid`) recarga tags y priorities. IDs no numéricos redirigen a `#/`.

---

## Pipeline de render (`js/render.js`)

```
render()
 ├── renderSidebar()    → nav items, botones de acción, avatar usuario
 ├── renderHeader()     → breadcrumb, título, botones contextuales
 └── renderContent()    → llama a la función de vista correspondiente:
      dashboard  → vDashboard()
      board/kanban → vBoard()
      board/tags  → vProjectTags()
      board/priorities → vProjectPriorities()
      board/team  → vProjectTeam()
      team        → vTeam()
```

Todas las funciones de vista retornan HTML como string y se insertan con `innerHTML`. El render es completo en cada ciclo (no virtual DOM).

---

## Sistema de modales (`js/modals/base.js`)

```javascript
showModal(html)   // inserta html en .modal-box y muestra #modal-bg
closeM()          // oculta el modal
bgClose(e)        // cierra si se hace click en el fondo
mhdr(title, sub)  // helper: cabecera estilizada del modal
mfoot(label, showDanger, dangerFn)  // helper: footer con botón guardar y optionalmente eliminar
swatches(sel, nm) // picker de 10 colores predefinidos
iconGrid(sel, nm) // picker de 25 iconos Material Symbols
```

Los modales de creación/edición siempre terminan con: `closeM() → await loadAll() → render() → toast(...)`.

---

## Módulos de vistas y modales

| Archivo | Funciones principales |
|---------|-----------------------|
| `views/dashboard.js` | `vDashboard()`, `projCard(p, taskStats, groupCounts)` |
| `views/board.js` | `vBoard()`, `kanbanCol(g)`, `taskCard(t)` |
| `views/team.js` | `vProjectTeam()`, `vTeam()` |
| `views/tags.js` | `vProjectTags()` |
| `views/priorities.js` | `vProjectPriorities()` |
| `modals/project.js` | `mProject(id?)`, `mProjectTeam()`, `mProjectMenu(id)` |
| `modals/group.js` | `mGroup(id?)`, `mColMenu(id)` |
| `modals/task.js` | `mTask(taskId?, groupId?)`, `saveTask()`, `renderTTagSection()`, `renderPrioritySection()` |
| `modals/tag.js` | `mProjectTags(pid)`, `mTag(id?)` |
| `modals/priority.js` | `mProjectPriorities(pid)`, `mPriority(id?)` |
| `modals/user.js` | `mUser()`, `mEditProfile()`, `mAdminEditUser(id)`, `confirmDelUser(id)` |
| `modals/subtask.js` | `loadTodos(taskId)`, `addTodo(taskId)`, `toggleTodo(taskId, todoId)` |
| `delete.js` | `confirmDel(type, id)`, `execDel(type, id)` |
| `dnd.js` | Drag & drop de tarjetas entre columnas y reordenación de columnas |

---

## Seguridad frontend

- **`esc(s)`** (`utils.js`): escapa HTML (`&`, `<`, `>`, `"`, `'`) — se usa siempre que se inserta user content en `innerHTML`.
- **`jsq(s)`** (`utils.js`): escapa para literales de string JS dentro de atributos `onclick` (escapa `\`, `'`, `"`, saltos de línea). Necesario para valores de texto en handlers inline.
- **`confirmDel(type, id)`**: recibe solo el ID numérico (seguro), busca el nombre en `S` internamente — evita inyección de strings en atributos onclick.
- Los IDs numéricos se interpolan directamente en `onclick` sin riesgo de inyección.

---

## Drag & Drop (`js/dnd.js`)

Implementación manual con eventos de ratón (`mousedown`, `mousemove`, `mouseup`):
- **Tarjetas:** arrastrar entre columnas → `PATCH /groups/{id}/tasks/reorder`
- **Columnas:** reordenar el tablero → `PATCH /groups/reorder`
- Indicadores visuales: clases CSS `drop-before` / `drop-after` en tarjetas, `col-reorder-before` / `col-reorder-after` en columnas.
