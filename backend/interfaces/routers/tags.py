from fastapi import APIRouter, Depends, HTTPException
from backend.application.tag_use_cases import TagUseCases
from backend.domain.entities import User
from backend.domain.exceptions import (
    GroupNotFound, TagNameAlreadyExists, TagNotFound, TagNotInProject, TaskNotFound,
)
from backend.interfaces.dependencies import (
    get_current_user, get_tag_use_cases, get_task_use_cases, get_group_use_cases,
    require_project_access, require_project_leader,
)
from backend.interfaces.schemas import TagCreate, TagResponse, TagUpdate

# ── CRUD (project-scoped) ─────────────────────────────────────────────────────
router = APIRouter(prefix="/projects/{project_id}/tags", tags=["tags"])


@router.get("/", response_model=list[TagResponse])
def list_tags(
    project_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
):
    require_project_access(project_id, current_user.id)
    return [TagResponse.from_entity(t) for t in use_cases.get_by_project(project_id)]


@router.get("/{tag_id}", response_model=TagResponse)
def get_tag(
    project_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
):
    require_project_access(project_id, current_user.id)
    try:
        tag = use_cases.get_by_id(tag_id)
    except TagNotFound:
        raise HTTPException(status_code=404, detail="Tag not found")
    if tag.project_id != project_id:
        raise HTTPException(status_code=404, detail="Tag not found")
    return TagResponse.from_entity(tag)


@router.post("/", response_model=TagResponse, status_code=201)
def create_tag(
    project_id: int,
    body: TagCreate,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
):
    require_project_leader(project_id, current_user.id)
    try:
        return TagResponse.from_entity(
            use_cases.create(name=body.name, color=body.color, project_id=project_id)
        )
    except TagNameAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.patch("/{tag_id}", response_model=TagResponse)
def update_tag(
    project_id: int,
    tag_id: int,
    body: TagUpdate,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
):
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")
    require_project_leader(project_id, current_user.id)
    try:
        tag = use_cases.get_by_id(tag_id)
    except TagNotFound:
        raise HTTPException(status_code=404, detail="Tag not found")
    if tag.project_id != project_id:
        raise HTTPException(status_code=404, detail="Tag not found")
    try:
        return TagResponse.from_entity(use_cases.update(tag_id, updates))
    except TagNotFound:
        raise HTTPException(status_code=404, detail="Tag not found")
    except TagNameAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.delete("/{tag_id}", status_code=204)
def delete_tag(
    project_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
):
    require_project_leader(project_id, current_user.id)
    try:
        tag = use_cases.get_by_id(tag_id)
    except TagNotFound:
        raise HTTPException(status_code=404, detail="Tag not found")
    if tag.project_id != project_id:
        raise HTTPException(status_code=404, detail="Tag not found")
    use_cases.delete(tag_id)


# ── Asignación Task ↔ Tag ────────────────────────────────────────────────────
assign_router = APIRouter(tags=["tag-assignments"])


def _task_project_id(task_id: int, task_uc) -> int | None:
    from backend.interfaces.routers.tasks import _group_project_id
    try:
        task = task_uc.get_by_id(task_id)
        return _group_project_id(task.group_id)
    except TaskNotFound:
        return None


def _group_project_id_direct(group_id: int, group_uc) -> int | None:
    try:
        return group_uc.get_by_id(group_id).project_id
    except GroupNotFound:
        return None


@assign_router.post("/tasks/{task_id}/tags/{tag_id}", status_code=204)
def assign_tag_to_task(
    task_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
    task_uc=Depends(get_task_use_cases),
):
    require_project_access(_task_project_id(task_id, task_uc), current_user.id)
    try:
        use_cases.assign_to_task(task_id, tag_id)
    except TaskNotFound:
        raise HTTPException(status_code=404, detail="Task not found")
    except TagNotFound:
        raise HTTPException(status_code=404, detail="Tag not found")
    except TagNotInProject as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@assign_router.delete("/tasks/{task_id}/tags/{tag_id}", status_code=204)
def unassign_tag_from_task(
    task_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
    task_uc=Depends(get_task_use_cases),
):
    require_project_access(_task_project_id(task_id, task_uc), current_user.id)
    try:
        use_cases.unassign_from_task(task_id, tag_id)
    except TaskNotFound:
        raise HTTPException(status_code=404, detail="Task not found")


# ── Asignación Group ↔ Tag ───────────────────────────────────────────────────

@assign_router.post("/groups/{group_id}/tags/{tag_id}", status_code=204)
def assign_tag_to_group(
    group_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
    group_uc=Depends(get_group_use_cases),
):
    require_project_access(_group_project_id_direct(group_id, group_uc), current_user.id)
    try:
        use_cases.assign_to_group(group_id, tag_id)
    except GroupNotFound:
        raise HTTPException(status_code=404, detail="Group not found")
    except TagNotFound:
        raise HTTPException(status_code=404, detail="Tag not found")
    except TagNotInProject as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@assign_router.delete("/groups/{group_id}/tags/{tag_id}", status_code=204)
def unassign_tag_from_group(
    group_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
    group_uc=Depends(get_group_use_cases),
):
    require_project_access(_group_project_id_direct(group_id, group_uc), current_user.id)
    try:
        use_cases.unassign_from_group(group_id, tag_id)
    except GroupNotFound:
        raise HTTPException(status_code=404, detail="Group not found")
