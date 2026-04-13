from app.domain.entities import Tag
from app.domain.exceptions import (
    GroupNotFound, TagNameAlreadyExists, TagNotFound, TagNotInProject, TaskNotFound,
)
from app.domain.repositories import GroupRepository, TagRepository, TaskRepository


class TagUseCases:
    def __init__(self, tag_repo: TagRepository, task_repo: TaskRepository, group_repo: GroupRepository):
        self._tags = tag_repo
        self._tasks = task_repo
        self._groups = group_repo

    def get_all(self) -> list[Tag]:
        return self._tags.get_all()

    def get_by_project(self, project_id: int) -> list[Tag]:
        return self._tags.get_by_project(project_id)

    def get_by_id(self, tag_id: int) -> Tag:
        tag = self._tags.get_by_id(tag_id)
        if tag is None:
            raise TagNotFound(tag_id)
        return tag

    def create(self, name: str, color: str, project_id: int) -> Tag:
        return self._tags.create(Tag(name=name, color=color, project_id=project_id))

    def update(self, tag_id: int, updates: dict) -> Tag:
        tag = self.get_by_id(tag_id)
        for key, value in updates.items():
            setattr(tag, key, value)
        return self._tags.update(tag)

    def delete(self, tag_id: int) -> None:
        self.get_by_id(tag_id)
        self._tags.delete(tag_id)

    def assign_to_task(self, task_id: int, tag_id: int) -> None:
        task = self._tasks.get_by_id(task_id)
        if task is None:
            raise TaskNotFound(task_id)
        tag = self.get_by_id(tag_id)
        group = self._groups.get_by_id(task.group_id)
        if group is not None and tag.project_id != group.project_id:
            raise TagNotInProject(tag_id, group.project_id)
        self._tags.assign_to_task(task_id, tag_id)

    def unassign_from_task(self, task_id: int, tag_id: int) -> None:
        if self._tasks.get_by_id(task_id) is None:
            raise TaskNotFound(task_id)
        self._tags.unassign_from_task(task_id, tag_id)

    def assign_to_group(self, group_id: int, tag_id: int) -> None:
        group = self._groups.get_by_id(group_id)
        if group is None:
            raise GroupNotFound(group_id)
        tag = self.get_by_id(tag_id)
        if tag.project_id != group.project_id:
            raise TagNotInProject(tag_id, group.project_id)
        self._tags.assign_to_group(group_id, tag_id)

    def unassign_from_group(self, group_id: int, tag_id: int) -> None:
        if self._groups.get_by_id(group_id) is None:
            raise GroupNotFound(group_id)
        self._tags.unassign_from_group(group_id, tag_id)
