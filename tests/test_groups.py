from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_project(client, headers, name="Test Project"):
    return client.post("/projects/", json={"name": name}, headers=headers).json()["id"]


def create_group(client: TestClient, headers, name="My group", description=None, project_id=None):
    if project_id is None:
        project_id = create_project(client, headers)
    return client.post("/groups/", json={"name": name, "description": description, "project_id": project_id}, headers=headers)


def create_task_in_group(client: TestClient, headers, group_id: int, title="Task"):
    return client.post("/tasks/", json={"title": title, "group_id": group_id}, headers=headers)


# ---------------------------------------------------------------------------
# POST /groups/
# ---------------------------------------------------------------------------

class TestCreateGroup:
    def test_creates_group_returns_201(self, client, auth):
        _, h = auth
        assert create_group(client, h).status_code == 201

    def test_response_has_correct_fields(self, client, auth):
        _, h = auth
        body = create_group(client, h, name="Sprint 1", description="First sprint").json()
        assert body["name"] == "Sprint 1"
        assert body["description"] == "First sprint"
        assert "id" in body
        assert "created_at" in body

    def test_description_can_be_null(self, client, auth):
        _, h = auth
        res = create_group(client, h, name="No desc")
        assert res.status_code == 201
        assert res.json()["description"] is None

    def test_empty_name_returns_422(self, client, auth):
        _, h = auth
        assert client.post("/groups/", json={"name": ""}, headers=h).status_code == 422

    def test_missing_name_returns_422(self, client, auth):
        _, h = auth
        assert client.post("/groups/", json={"description": "no name"}, headers=h).status_code == 422

    def test_name_too_long_returns_422(self, client, auth):
        _, h = auth
        assert client.post("/groups/", json={"name": "x" * 101}, headers=h).status_code == 422

    def test_unauthenticated_returns_401(self, client):
        assert client.post("/groups/", json={"name": "X"}).status_code == 401


# ---------------------------------------------------------------------------
# GET /groups/
# ---------------------------------------------------------------------------

class TestListGroups:
    def test_empty_list(self, client, auth):
        _, h = auth
        assert client.get("/groups/", headers=h).json() == []

    def test_returns_all_groups(self, client, auth):
        _, h = auth
        create_group(client, h, name="A")
        create_group(client, h, name="B")
        assert len(client.get("/groups/", headers=h).json()) == 2

    def test_groups_ordered_by_id(self, client, auth):
        _, h = auth
        create_group(client, h, name="First")
        create_group(client, h, name="Second")
        names = [g["name"] for g in client.get("/groups/", headers=h).json()]
        assert names == ["First", "Second"]


# ---------------------------------------------------------------------------
# GET /groups/{id}
# ---------------------------------------------------------------------------

class TestGetGroup:
    def test_returns_existing_group(self, client, auth):
        _, h = auth
        gid = create_group(client, h, name="Find me").json()["id"]
        assert client.get(f"/groups/{gid}", headers=h).json()["name"] == "Find me"

    def test_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.get("/groups/9999", headers=h).status_code == 404

    def test_404_has_detail_message(self, client, auth):
        _, h = auth
        assert "detail" in client.get("/groups/9999", headers=h).json()


# ---------------------------------------------------------------------------
# GET /groups/{id}/tasks
# ---------------------------------------------------------------------------

class TestListGroupTasks:
    def test_empty_task_list(self, client, auth):
        _, h = auth
        gid = create_group(client, h).json()["id"]
        assert client.get(f"/groups/{gid}/tasks", headers=h).json() == []

    def test_returns_only_tasks_of_group(self, client, auth):
        _, h = auth
        gid1 = create_group(client, h, name="G1").json()["id"]
        gid2 = create_group(client, h, name="G2").json()["id"]
        create_task_in_group(client, h, gid1, "Task A")
        create_task_in_group(client, h, gid1, "Task B")
        create_task_in_group(client, h, gid2, "Task C")
        tasks = client.get(f"/groups/{gid1}/tasks", headers=h).json()
        assert len(tasks) == 2

    def test_all_tasks_belong_to_group(self, client, auth):
        _, h = auth
        gid = create_group(client, h).json()["id"]
        create_task_in_group(client, h, gid, "T1")
        create_task_in_group(client, h, gid, "T2")
        tasks = client.get(f"/groups/{gid}/tasks", headers=h).json()
        assert all(t["group_id"] == gid for t in tasks)

    def test_group_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.get("/groups/9999/tasks", headers=h).status_code == 404


# ---------------------------------------------------------------------------
# PATCH /groups/{id}
# ---------------------------------------------------------------------------

class TestUpdateGroup:
    def test_update_name(self, client, auth):
        _, h = auth
        gid = create_group(client, h).json()["id"]
        assert client.patch(f"/groups/{gid}", json={"name": "Renamed"}, headers=h).json()["name"] == "Renamed"

    def test_update_description(self, client, auth):
        _, h = auth
        gid = create_group(client, h).json()["id"]
        assert client.patch(f"/groups/{gid}", json={"description": "New desc"}, headers=h).json()["description"] == "New desc"

    def test_partial_update_preserves_name(self, client, auth):
        _, h = auth
        gid = create_group(client, h, name="Keep").json()["id"]
        client.patch(f"/groups/{gid}", json={"description": "Updated"}, headers=h)
        assert client.get(f"/groups/{gid}", headers=h).json()["name"] == "Keep"

    def test_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.patch("/groups/9999", json={"name": "X"}, headers=h).status_code == 404

    def test_empty_body_returns_422(self, client, auth):
        _, h = auth
        gid = create_group(client, h).json()["id"]
        assert client.patch(f"/groups/{gid}", json={}, headers=h).status_code == 422


# ---------------------------------------------------------------------------
# DELETE /groups/{id}
# ---------------------------------------------------------------------------

class TestDeleteGroup:
    def test_delete_empty_group_returns_204(self, client, auth):
        _, h = auth
        gid = create_group(client, h).json()["id"]
        assert client.delete(f"/groups/{gid}", headers=h).status_code == 204

    def test_deleted_group_no_longer_exists(self, client, auth):
        _, h = auth
        gid = create_group(client, h).json()["id"]
        client.delete(f"/groups/{gid}", headers=h)
        assert client.get(f"/groups/{gid}", headers=h).status_code == 404

    def test_delete_group_with_tasks_cascades(self, client, auth):
        _, h = auth
        gid = create_group(client, h).json()["id"]
        create_task_in_group(client, h, gid)
        assert client.delete(f"/groups/{gid}", headers=h).status_code == 204

    def test_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.delete("/groups/9999", headers=h).status_code == 404
