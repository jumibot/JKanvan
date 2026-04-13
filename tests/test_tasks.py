from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_user(client: TestClient, headers, name="Alice", email="alice@test.com", password="secret123"):
    return client.post("/users/", json={"name": name, "email": email, "password": password}).json()["id"]


def create_project(client, headers):
    return client.post("/projects/", json={"name": "Test Project"}, headers=headers).json()["id"]


def create_group(client: TestClient, headers, name="Default group"):
    pid = create_project(client, headers)
    return client.post("/groups/", json={"name": name, "project_id": pid}, headers=headers).json()["id"]


def create_task(client: TestClient, headers, title="Test task", description="Desc",
                completed=False, group_id: int | None = None):
    if group_id is None:
        group_id = create_group(client, headers)
    return client.post("/tasks/", json={
        "title": title,
        "description": description,
        "completed": completed,
        "group_id": group_id,
    }, headers=headers)


# ---------------------------------------------------------------------------
# POST /tasks/
# ---------------------------------------------------------------------------

class TestCreateTask:
    def test_creates_task_returns_201(self, client, auth):
        _, h = auth
        assert create_task(client, h).status_code == 201

    def test_response_has_correct_fields(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        body = create_task(client, h, title="My task", description="Details", group_id=gid).json()
        assert body["title"] == "My task"
        assert body["description"] == "Details"
        assert body["completed"] is False
        assert body["group_id"] == gid
        assert "id" in body
        assert "created_at" in body
        assert "user" in body

    def test_completed_defaults_to_false(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        assert client.post("/tasks/", json={"title": "No completed", "group_id": gid}, headers=h).json()["completed"] is False

    def test_description_can_be_null(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        res = client.post("/tasks/", json={"title": "No desc", "group_id": gid}, headers=h)
        assert res.status_code == 201
        assert res.json()["description"] is None

    def test_with_user_id(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        uid = create_user(client, h)
        res = client.post("/tasks/", json={"title": "With user", "group_id": gid, "user_id": uid}, headers=h)
        assert res.status_code == 201
        assert res.json()["user"]["id"] == uid

    def test_invalid_user_id_returns_404(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        assert client.post("/tasks/", json={"title": "Bad user", "group_id": gid, "user_id": 9999}, headers=h).status_code == 404

    def test_invalid_group_returns_404(self, client, auth):
        _, h = auth
        assert client.post("/tasks/", json={"title": "Bad group", "group_id": 9999}, headers=h).status_code == 404

    def test_missing_group_id_returns_422(self, client, auth):
        _, h = auth
        assert client.post("/tasks/", json={"title": "No group"}, headers=h).status_code == 422

    def test_empty_title_returns_422(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        assert client.post("/tasks/", json={"title": "", "group_id": gid}, headers=h).status_code == 422

    def test_missing_title_returns_422(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        assert client.post("/tasks/", json={"description": "no title", "group_id": gid}, headers=h).status_code == 422

    def test_title_too_long_returns_422(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        assert client.post("/tasks/", json={"title": "x" * 201, "group_id": gid}, headers=h).status_code == 422

    def test_unauthenticated_returns_401(self, client):
        assert client.post("/tasks/", json={"title": "X", "group_id": 1}).status_code == 401


# ---------------------------------------------------------------------------
# GET /tasks/
# ---------------------------------------------------------------------------

class TestListTasks:
    def test_empty_list(self, client, auth):
        _, h = auth
        assert client.get("/tasks/", headers=h).json() == []

    def test_returns_all_tasks(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        create_task(client, h, title="Task A", group_id=gid)
        create_task(client, h, title="Task B", group_id=gid)
        assert len(client.get("/tasks/", headers=h).json()) == 2

    def test_tasks_ordered_by_id(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        create_task(client, h, title="First", group_id=gid)
        create_task(client, h, title="Second", group_id=gid)
        titles = [t["title"] for t in client.get("/tasks/", headers=h).json()]
        assert titles == ["First", "Second"]


# ---------------------------------------------------------------------------
# GET /tasks/{id}
# ---------------------------------------------------------------------------

class TestGetTask:
    def test_returns_existing_task(self, client, auth):
        _, h = auth
        task_id = create_task(client, h, title="Find me").json()["id"]
        assert client.get(f"/tasks/{task_id}", headers=h).json()["title"] == "Find me"

    def test_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.get("/tasks/9999", headers=h).status_code == 404

    def test_404_has_detail_message(self, client, auth):
        _, h = auth
        assert "detail" in client.get("/tasks/9999", headers=h).json()


# ---------------------------------------------------------------------------
# PATCH /tasks/{id}
# ---------------------------------------------------------------------------

class TestUpdateTask:
    def test_update_title(self, client, auth):
        _, h = auth
        task_id = create_task(client, h, title="Old title").json()["id"]
        assert client.patch(f"/tasks/{task_id}", json={"title": "New title"}, headers=h).json()["title"] == "New title"

    def test_update_sets_modified_at(self, client, auth):
        _, h = auth
        task_id = create_task(client, h).json()["id"]
        assert client.patch(f"/tasks/{task_id}", json={"title": "Updated"}, headers=h).json()["modified_at"] is not None

    def test_update_completed(self, client, auth):
        _, h = auth
        task_id = create_task(client, h).json()["id"]
        assert client.patch(f"/tasks/{task_id}", json={"completed": True}, headers=h).json()["completed"] is True

    def test_update_description(self, client, auth):
        _, h = auth
        task_id = create_task(client, h, description="Old").json()["id"]
        assert client.patch(f"/tasks/{task_id}", json={"description": "New desc"}, headers=h).json()["description"] == "New desc"

    def test_update_group(self, client, auth):
        _, h = auth
        pid = create_project(client, h)
        gid1 = client.post("/groups/", json={"name": "G1", "project_id": pid}, headers=h).json()["id"]
        gid2 = client.post("/groups/", json={"name": "G2", "project_id": pid}, headers=h).json()["id"]
        task_id = create_task(client, h, group_id=gid1).json()["id"]
        assert client.patch(f"/tasks/{task_id}", json={"group_id": gid2}, headers=h).json()["group_id"] == gid2

    def test_update_group_cross_project_returns_400(self, client, auth):
        _, h = auth
        gid1 = create_group(client, h, name="G1")   # project A (auto-created)
        gid2 = create_group(client, h, name="G2")   # project B (auto-created)
        task_id = create_task(client, h, group_id=gid1).json()["id"]
        assert client.patch(f"/tasks/{task_id}", json={"group_id": gid2}, headers=h).status_code == 400

    def test_update_user_id(self, client, auth):
        _, h = auth
        task_id = create_task(client, h).json()["id"]
        uid = create_user(client, h)
        assert client.patch(f"/tasks/{task_id}", json={"user_id": uid}, headers=h).json()["user"]["id"] == uid

    def test_update_group_invalid_returns_404(self, client, auth):
        _, h = auth
        task_id = create_task(client, h).json()["id"]
        assert client.patch(f"/tasks/{task_id}", json={"group_id": 9999}, headers=h).status_code == 404

    def test_partial_update_preserves_other_fields(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        task_id = create_task(client, h, title="Keep me", description="Also keep", group_id=gid).json()["id"]
        client.patch(f"/tasks/{task_id}", json={"completed": True}, headers=h)
        body = client.get(f"/tasks/{task_id}", headers=h).json()
        assert body["title"] == "Keep me"
        assert body["description"] == "Also keep"
        assert body["group_id"] == gid

    def test_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.patch("/tasks/9999", json={"title": "Ghost"}, headers=h).status_code == 404

    def test_empty_body_returns_422(self, client, auth):
        _, h = auth
        task_id = create_task(client, h).json()["id"]
        assert client.patch(f"/tasks/{task_id}", json={}, headers=h).status_code == 422

    def test_invalid_title_returns_422(self, client, auth):
        _, h = auth
        task_id = create_task(client, h).json()["id"]
        assert client.patch(f"/tasks/{task_id}", json={"title": ""}, headers=h).status_code == 422


# ---------------------------------------------------------------------------
# DELETE /tasks/{id}
# ---------------------------------------------------------------------------

class TestDeleteTask:
    def test_delete_existing_returns_204(self, client, auth):
        _, h = auth
        task_id = create_task(client, h).json()["id"]
        assert client.delete(f"/tasks/{task_id}", headers=h).status_code == 204

    def test_deleted_task_no_longer_exists(self, client, auth):
        _, h = auth
        task_id = create_task(client, h).json()["id"]
        client.delete(f"/tasks/{task_id}", headers=h)
        assert client.get(f"/tasks/{task_id}", headers=h).status_code == 404

    def test_deleted_task_not_in_list(self, client, auth):
        _, h = auth
        gid = create_group(client, h)
        task_id = create_task(client, h, title="Delete me", group_id=gid).json()["id"]
        create_task(client, h, title="Keep me", group_id=gid)
        client.delete(f"/tasks/{task_id}", headers=h)
        titles = [t["title"] for t in client.get("/tasks/", headers=h).json()]
        assert "Delete me" not in titles
        assert "Keep me" in titles

    def test_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.delete("/tasks/9999", headers=h).status_code == 404
