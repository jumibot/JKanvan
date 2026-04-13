from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_project(client, headers):
    return client.post("/projects/", json={"name": "Test Project"}, headers=headers).json()["id"]


def create_group(client: TestClient, headers, name="Group"):
    pid = create_project(client, headers)
    return client.post("/groups/", json={"name": name, "project_id": pid}, headers=headers).json()["id"]


def create_task(client: TestClient, headers, group_id: int, title="Task"):
    return client.post("/tasks/", json={"title": title, "group_id": group_id}, headers=headers).json()["id"]


def create_todo(client: TestClient, headers, task_id: int, title="Todo item", completed=False, order=None):
    payload = {"title": title, "completed": completed}
    if order is not None:
        payload["order"] = order
    return client.post(f"/tasks/{task_id}/todos", json=payload, headers=headers)


# ---------------------------------------------------------------------------
# POST /tasks/{task_id}/todos
# ---------------------------------------------------------------------------

class TestCreateTodo:
    def test_creates_todo_returns_201(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        assert create_todo(client, h, tid).status_code == 201

    def test_response_has_correct_fields(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        body = create_todo(client, h, tid, title="My todo", completed=False).json()
        assert body["title"] == "My todo"
        assert body["completed"] is False
        assert body["task_id"] == tid
        assert "id" in body and "order" in body

    def test_completed_defaults_to_false(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        assert client.post(f"/tasks/{tid}/todos", json={"title": "Default"}, headers=h).json()["completed"] is False

    def test_order_auto_assigned(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        o1 = create_todo(client, h, tid, title="A").json()["order"]
        o2 = create_todo(client, h, tid, title="B").json()["order"]
        assert o2 > o1

    def test_explicit_order_respected(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        assert create_todo(client, h, tid, order=99).json()["order"] == 99

    def test_task_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.post("/tasks/9999/todos", json={"title": "Ghost"}, headers=h).status_code == 404

    def test_empty_title_returns_422(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        assert client.post(f"/tasks/{tid}/todos", json={"title": ""}, headers=h).status_code == 422

    def test_unauthenticated_returns_401(self, client):
        assert client.post("/tasks/1/todos", json={"title": "Ghost"}).status_code == 401


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}/todos
# ---------------------------------------------------------------------------

class TestListTodos:
    def test_empty_list(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        assert client.get(f"/tasks/{tid}/todos", headers=h).json() == []

    def test_returns_all_todos(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        create_todo(client, h, tid, title="A")
        create_todo(client, h, tid, title="B")
        assert len(client.get(f"/tasks/{tid}/todos", headers=h).json()) == 2

    def test_todos_ordered_by_sort_order(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        create_todo(client, h, tid, title="Last",  order=10)
        create_todo(client, h, tid, title="First", order=1)
        titles = [t["title"] for t in client.get(f"/tasks/{tid}/todos", headers=h).json()]
        assert titles == ["First", "Last"]

    def test_only_returns_todos_of_task(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid1 = create_task(client, h, gid, title="T1")
        tid2 = create_task(client, h, gid, title="T2")
        create_todo(client, h, tid1, title="For T1")
        create_todo(client, h, tid2, title="For T2")
        todos = client.get(f"/tasks/{tid1}/todos", headers=h).json()
        assert len(todos) == 1
        assert todos[0]["title"] == "For T1"

    def test_task_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.get("/tasks/9999/todos", headers=h).status_code == 404


# ---------------------------------------------------------------------------
# PATCH /tasks/{task_id}/todos/{todo_id}
# ---------------------------------------------------------------------------

class TestUpdateTodo:
    def test_mark_completed(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        todo_id = create_todo(client, h, tid).json()["id"]
        assert client.patch(f"/tasks/{tid}/todos/{todo_id}", json={"completed": True}, headers=h).json()["completed"] is True

    def test_update_title(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        todo_id = create_todo(client, h, tid, title="Old").json()["id"]
        assert client.patch(f"/tasks/{tid}/todos/{todo_id}", json={"title": "New"}, headers=h).json()["title"] == "New"

    def test_update_order(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        todo_id = create_todo(client, h, tid).json()["id"]
        assert client.patch(f"/tasks/{tid}/todos/{todo_id}", json={"order": 5}, headers=h).json()["order"] == 5

    def test_task_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.patch("/tasks/9999/todos/1", json={"completed": True}, headers=h).status_code == 404

    def test_todo_not_found_returns_404(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        assert client.patch(f"/tasks/{tid}/todos/9999", json={"completed": True}, headers=h).status_code == 404

    def test_todo_belongs_to_other_task_returns_404(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid1 = create_task(client, h, gid, title="T1")
        tid2 = create_task(client, h, gid, title="T2")
        todo_id = create_todo(client, h, tid1).json()["id"]
        assert client.patch(f"/tasks/{tid2}/todos/{todo_id}", json={"completed": True}, headers=h).status_code == 404

    def test_empty_body_returns_422(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        todo_id = create_todo(client, h, tid).json()["id"]
        assert client.patch(f"/tasks/{tid}/todos/{todo_id}", json={}, headers=h).status_code == 422


# ---------------------------------------------------------------------------
# DELETE /tasks/{task_id}/todos/{todo_id}
# ---------------------------------------------------------------------------

class TestDeleteTodo:
    def test_delete_returns_204(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        todo_id = create_todo(client, h, tid).json()["id"]
        assert client.delete(f"/tasks/{tid}/todos/{todo_id}", headers=h).status_code == 204

    def test_deleted_todo_not_in_list(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        todo_id = create_todo(client, h, tid, title="Delete me").json()["id"]
        create_todo(client, h, tid, title="Keep me")
        client.delete(f"/tasks/{tid}/todos/{todo_id}", headers=h)
        titles = [t["title"] for t in client.get(f"/tasks/{tid}/todos", headers=h).json()]
        assert "Delete me" not in titles and "Keep me" in titles

    def test_task_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.delete("/tasks/9999/todos/1", headers=h).status_code == 404

    def test_todo_not_found_returns_404(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        assert client.delete(f"/tasks/{tid}/todos/9999", headers=h).status_code == 404


# ---------------------------------------------------------------------------
# Todo counter in TaskResponse
# ---------------------------------------------------------------------------

class TestTodoCountsInTask:
    def test_task_has_todo_counts(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        create_todo(client, h, tid, title="A", completed=False)
        create_todo(client, h, tid, title="B", completed=True)
        body = client.get(f"/tasks/{tid}", headers=h).json()
        assert body["todos_total"] == 2
        assert body["todos_completed"] == 1

    def test_task_without_todos_has_zero_counts(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        body = client.get(f"/tasks/{tid}", headers=h).json()
        assert body["todos_total"] == 0
        assert body["todos_completed"] == 0

    def test_delete_task_cascades_todos(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        tid = create_task(client, h, gid)
        create_todo(client, h, tid)
        client.delete(f"/tasks/{tid}", headers=h)
        assert client.get(f"/tasks/{tid}/todos", headers=h).status_code == 404
