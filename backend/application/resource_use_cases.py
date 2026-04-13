from datetime import datetime
from backend.domain.entities import Resource
from backend.domain.exceptions import EmailAlreadyExists, ResourceNotFound
from backend.domain.repositories import ResourceRepository


class ResourceUseCases:
    def __init__(self, resource_repo: ResourceRepository):
        self._resources = resource_repo

    def get_all(self) -> list[Resource]:
        return self._resources.get_all()

    def get_by_id(self, resource_id: int) -> Resource:
        resource = self._resources.get_by_id(resource_id)
        if resource is None:
            raise ResourceNotFound(resource_id)
        return resource

    def create(self, name: str, email: str, avatar_url: str | None) -> Resource:
        if self._resources.get_by_email(email) is not None:
            raise EmailAlreadyExists(email)
        return self._resources.create(Resource(name=name, email=email, avatar_url=avatar_url))

    def update(self, resource_id: int, updates: dict) -> Resource:
        resource = self.get_by_id(resource_id)  # raises ResourceNotFound
        if "email" in updates:
            existing = self._resources.get_by_email(updates["email"])
            if existing is not None and existing.id != resource_id:
                raise EmailAlreadyExists(updates["email"])
        for key, value in updates.items():
            setattr(resource, key, value)
        return self._resources.update(resource)

    def delete(self, resource_id: int) -> None:
        self.get_by_id(resource_id)  # raises ResourceNotFound
        self._resources.delete(resource_id)
