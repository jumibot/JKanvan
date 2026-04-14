# Modelo de datos

## Índice

- [Entidades principales](#entidades-principales)
  - [User](#user)
  - [Project](#project)
  - [Group](#group-columna-kanban)
  - [Task](#task)
  - [Priority](#priority-scoped-a-proyecto)
  - [Tag](#tag-scoped-a-proyecto)
  - [TodoItem](#todoitem-subtarea)
- [Tablas de unión](#tablas-de-unión)
- [Relaciones y cascadas](#relaciones-y-cascadas)
- [Restricciones de integridad notables](#restricciones-de-integridad-notables)

---

## Entidades principales

### User
| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | autoincrement |
| name | str (1-100) | |
| email | str único | lowercase, validado |
| password_hash | str | `pbkdf2$<salt_hex>$<hash_hex>` |
| avatar_url | str? | URL libre |
| is_admin | bool | false por defecto |
| created_at / modified_at | datetime? | |
| created_by / modified_by | int? | FK a users.id |

### Project
| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| name | str (1-100) | |
| description | str? | |
| icon | str | nombre icono Material Symbols, default `folder` |
| color | str | hex #RRGGBB, default `#3B82F6` |
| owner_id | int FK | → users, NOT NULL |
| leader_id | int FK? | → users, ON DELETE SET NULL; default = owner al crear |
| priority_id | int FK? | → priorities, ON DELETE SET NULL |
| members | list[User] | via tabla `project_members` |

### Group (columna Kanban)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| name | str (1-100) | |
| description | str? | |
| color | str | hex #RRGGBB |
| project_id | int FK | → projects, ON DELETE CASCADE |
| sort_order | int | orden de la columna (0-indexed) |

### Task
| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| group_id | int FK | → groups, ON DELETE CASCADE |
| title | str (1-200) | |
| description | str? | |
| completed | bool | false por defecto |
| user_id | int FK? | → users, ON DELETE SET NULL (responsable) |
| priority_id | int FK? | → priorities, ON DELETE SET NULL |
| estimated_duration | float? | horas |
| estimated_start / estimated_end | datetime? | |
| actual_start / actual_end | datetime? | |
| sort_order | int | orden dentro del grupo |
| tags | list[Tag] | via tabla `task_tags` |
| todos_total / todos_completed | int | computed al leer |

### Priority *(scoped a proyecto)*
| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| name | str (1-50) | único por proyecto |
| icon | str | nombre icono Material Symbols, default `flag` |
| color | str | hex #RRGGBB |
| project_id | int FK | → projects, ON DELETE CASCADE |

### Tag *(scoped a proyecto)*
| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| name | str (1-50) | único por proyecto |
| color | str | hex #RRGGBB |
| project_id | int FK | → projects, ON DELETE CASCADE |

### TodoItem (subtarea)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| task_id | int FK | → tasks, ON DELETE CASCADE |
| title | str (1-200) | |
| completed | bool | |
| order | int | orden dentro de la tarea |

---

## Tablas de unión

| Tabla | Columnas | Propósito |
|-------|----------|-----------|
| `project_members` | (project_id, user_id) PK | membresía al proyecto |
| `task_tags` | (task_id, tag_id) PK | etiquetas de una tarea |
| `group_tags` | (group_id, tag_id) PK | etiquetas de un grupo |

---

## Relaciones y cascadas

```
User
 └─< Project (owner_id)          → SET NULL al borrar user
 └─< Project (leader_id)         → SET NULL al borrar user
 └─< project_members             → CASCADE al borrar user/project

Project
 └─< Priority                    → CASCADE
 └─< Tag                         → CASCADE
 └─< Group
      └─< Task
           └─< TodoItem          → CASCADE
           └─< task_tags         → CASCADE
```

Borrar un **Proyecto** elimina en cascada: grupos, tareas, todos, tags, prioridades, membresías.  
Borrar un **Usuario** (operación admin) requiere primero borrar o transferir sus proyectos; existe el endpoint de cascade-delete con confirmación de contraseña.

---

## Restricciones de integridad notables

- `priorities.name` + `priorities.project_id` → UNIQUE
- `tags.name` + `tags.project_id` → UNIQUE
- `users.email` → UNIQUE
- Colores validados como hex `#RRGGBB` en Pydantic (schemas) y con CHECK en SQLite
- `is_admin` → CHECK (0 o 1)
