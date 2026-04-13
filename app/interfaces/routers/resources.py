from fastapi import APIRouter, Depends, HTTPException
from app.application.resource_use_cases import ResourceUseCases
from app.domain.exceptions import EmailAlreadyExists, ResourceNotFound
from app.interfaces.dependencies import get_resource_use_cases
from app.interfaces.schemas import ResourceCreate, ResourceResponse, ResourceUpdate

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("/", response_model=list[ResourceResponse])
def list_resources(use_cases: ResourceUseCases = Depends(get_resource_use_cases)):
    return [ResourceResponse.from_entity(r) for r in use_cases.get_all()]


@router.get("/{resource_id}", response_model=ResourceResponse)
def get_resource(resource_id: int, use_cases: ResourceUseCases = Depends(get_resource_use_cases)):
    try:
        return ResourceResponse.from_entity(use_cases.get_by_id(resource_id))
    except ResourceNotFound:
        raise HTTPException(status_code=404, detail="Resource not found")


@router.post("/", response_model=ResourceResponse, status_code=201)
def create_resource(body: ResourceCreate, use_cases: ResourceUseCases = Depends(get_resource_use_cases)):
    try:
        resource = use_cases.create(name=body.name, email=body.email, avatar_url=body.avatar_url)
        return ResourceResponse.from_entity(resource)
    except EmailAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.patch("/{resource_id}", response_model=ResourceResponse)
def update_resource(resource_id: int, body: ResourceUpdate, use_cases: ResourceUseCases = Depends(get_resource_use_cases)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")
    try:
        return ResourceResponse.from_entity(use_cases.update(resource_id, updates))
    except ResourceNotFound:
        raise HTTPException(status_code=404, detail="Resource not found")
    except EmailAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.delete("/{resource_id}", status_code=204)
def delete_resource(resource_id: int, use_cases: ResourceUseCases = Depends(get_resource_use_cases)):
    try:
        use_cases.delete(resource_id)
    except ResourceNotFound:
        raise HTTPException(status_code=404, detail="Resource not found")
