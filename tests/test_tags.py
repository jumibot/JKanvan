from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_project(client: TestClient, headers, name="Test Project"):
    r = client.post("/projects/", json={"name": name}, headers=headers)
    return r.json()["id"]


def add_member(client: TestClient, headers, project_id: int, user_id: int):
    client.post(f"/projects/{project_id}/members/{user_id}", headers=headers)


def create_tag(client: TestClient, headers, project_id: int, name="Backend", color="#3B82F6"):
    return client.post(
        f"/projects/{project_id}/tags/",
        json={"name": name, "color": color},
        headers=headers,
    )


def create_group(client: TestClient, headers, project_id: int, name="Group"):
    return client.post(
        "/groups/", json={"name": name, "project_id": project_id}, headers=headers
    ).json()["id"]


def create_task(client: TestClient, headers, group_id: int, title="Task"):
    return client.post(
        "/tasks/", json={"title": title, "group_id": group_id}, headers=headers
    ).json()["id"]


def register_and_login(client: TestClient, email: str, password: str = "pass1234"):
    """Returns (headers, user_id)."""
    r = client.post("/users/", json={"name": "User", "email": email, "password": password})
    user_id = r.json()["id"]
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, user_id


# ---------------------------------------------------------------------------
# POST /projects/{project_id}/tags/
# ---------------------------------------------------------------------------

class TestCreateTag:
    def test_creates_tag_returns_201(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        assert create_tag(client, h, pid).status_code == 201

    def test_response_fields(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        body = create_tag(client, h, pid, name="Frontend", color="#F97316").json()
        assert body["name"] == "Frontend"
        assert body["color"] == "#F97316"
        assert body["project_id"] == pid
        assert "id" in body

    def test_color_is_uppercased(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        assert create_tag(client, h, pid, color="#3b82f6").json()["color"] == "#3B82F6"

    def test_duplicate_name_in_same_project_returns_409(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        create_tag(client, h, pid, name="Unique")
        assert create_tag(client, h, pid, name="Unique").status_code == 409

    def test_duplicate_name_in_different_project_is_allowed(self, client, auth):
        user, h = auth
        pid1 = create_project(client, h, name="Project A")
        pid2 = create_project(client, h, name="Project B")
        create_tag(client, h, pid1, name="Sprint")
        assert create_tag(client, h, pid2, name="Sprint").status_code == 201

    def test_invalid_color_returns_422(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        r = client.post(f"/projects/{pid}/tags/", json={"name": "Bad", "color": "notacolor"}, headers=h)
        assert r.status_code == 422

    def test_missing_name_returns_422(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        assert client.post(f"/projects/{pid}/tags/", json={"color": "#000000"}, headers=h).status_code == 422

    def test_unauthenticated_returns_401(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        assert client.post(f"/projects/{pid}/tags/", json={"name": "X", "color": "#000000"}).status_code == 401

    def test_member_cannot_create_tag_returns_403(self, client, auth):
        owner, h_owner = auth
        pid = create_project(client, h_owner)
        h_member, member_id = register_and_login(client, "member@test.com")
        add_member(client, h_owner, pid, member_id)
        assert create_tag(client, h_member, pid).status_code == 403

    def test_non_member_cannot_create_tag_returns_403(self, client, auth):
        owner, h_owner = auth
        pid = create_project(client, h_owner)
        h_other, _ = register_and_login(client, "other@test.com")
        assert create_tag(client, h_other, pid).status_code == 403


# ---------------------------------------------------------------------------
# GET /projects/{project_id}/tags/ and /{tag_id}
# ---------------------------------------------------------------------------

class TestGetTags:
    def test_empty_list(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        assert client.get(f"/projects/{pid}/tags/", headers=h).json() == []

    def test_returns_project_tags_only(self, client, auth):
        user, h = auth
        pid1 = create_project(client, h, name="P1")
        pid2 = create_project(client, h, name="P2")
        create_tag(client, h, pid1, name="A")
        create_tag(client, h, pid1, name="B")
        create_tag(client, h, pid2, name="C")
        tags = client.get(f"/projects/{pid1}/tags/", headers=h).json()
        assert len(tags) == 2
        assert all(t["project_id"] == pid1 for t in tags)

    def test_get_by_id(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        tag_id = create_tag(client, h, pid, name="Find me").json()["id"]
        assert client.get(f"/projects/{pid}/tags/{tag_id}", headers=h).json()["name"] == "Find me"

    def test_not_found_returns_404(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        assert client.get(f"/projects/{pid}/tags/9999", headers=h).status_code == 404

    def test_tag_from_other_project_returns_404(self, client, auth):
        user, h = auth
        pid1 = create_project(client, h, name="P1")
        pid2 = create_project(client, h, name="P2")
        tag_id = create_tag(client, h, pid1, name="Only in P1").json()["id"]
        assert client.get(f"/projects/{pid2}/tags/{tag_id}", headers=h).status_code == 404

    def test_member_can_list_tags(self, client, auth):
        owner, h_owner = auth
        pid = create_project(client, h_owner)
        create_tag(client, h_owner, pid, name="Shared")
        h_member, member_id = register_and_login(client, "viewer@test.com")
        add_member(client, h_owner, pid, member_id)
        tags = client.get(f"/projects/{pid}/tags/", headers=h_member).json()
        assert len(tags) == 1

    def test_non_member_cannot_list_tags_returns_403(self, client, auth):
        owner, h_owner = auth
        pid = create_project(client, h_owner)
        h_other, _ = register_and_login(client, "outsider@test.com")
        assert client.get(f"/projects/{pid}/tags/", headers=h_other).status_code == 403


# ---------------------------------------------------------------------------
# PATCH /projects/{project_id}/tags/{tag_id}
# ---------------------------------------------------------------------------

class TestUpdateTag:
    def test_update_name(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        tag_id = create_tag(client, h, pid, name="Old").json()["id"]
        r = client.patch(f"/projects/{pid}/tags/{tag_id}", json={"name": "New"}, headers=h)
        assert r.json()["name"] == "New"

    def test_update_color(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        tag_id = create_tag(client, h, pid).json()["id"]
        r = client.patch(f"/projects/{pid}/tags/{tag_id}", json={"color": "#ffffff"}, headers=h)
        assert r.json()["color"] == "#FFFFFF"

    def test_duplicate_name_returns_409(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        create_tag(client, h, pid, name="Other", color="#111111")
        tag_id = create_tag(client, h, pid).json()["id"]
        assert client.patch(f"/projects/{pid}/tags/{tag_id}", json={"name": "Other"}, headers=h).status_code == 409

    def test_not_found_returns_404(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        assert client.patch(f"/projects/{pid}/tags/9999", json={"name": "Ghost"}, headers=h).status_code == 404

    def test_empty_body_returns_422(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        tag_id = create_tag(client, h, pid).json()["id"]
        assert client.patch(f"/projects/{pid}/tags/{tag_id}", json={}, headers=h).status_code == 422

    def test_member_cannot_update_tag_returns_403(self, client, auth):
        owner, h_owner = auth
        pid = create_project(client, h_owner)
        tag_id = create_tag(client, h_owner, pid, name="Managed").json()["id"]
        h_member, member_id = register_and_login(client, "mem2@test.com")
        add_member(client, h_owner, pid, member_id)
        assert client.patch(
            f"/projects/{pid}/tags/{tag_id}", json={"name": "Hacked"}, headers=h_member
        ).status_code == 403


# ---------------------------------------------------------------------------
# DELETE /projects/{project_id}/tags/{tag_id}
# ---------------------------------------------------------------------------

class TestDeleteTag:
    def test_delete_returns_204(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        tag_id = create_tag(client, h, pid).json()["id"]
        assert client.delete(f"/projects/{pid}/tags/{tag_id}", headers=h).status_code == 204

    def test_not_found_returns_404(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        assert client.delete(f"/projects/{pid}/tags/9999", headers=h).status_code == 404

    def test_member_cannot_delete_tag_returns_403(self, client, auth):
        owner, h_owner = auth
        pid = create_project(client, h_owner)
        tag_id = create_tag(client, h_owner, pid, name="Protected").json()["id"]
        h_member, member_id = register_and_login(client, "mem3@test.com")
        add_member(client, h_owner, pid, member_id)
        assert client.delete(f"/projects/{pid}/tags/{tag_id}", headers=h_member).status_code == 403


# ---------------------------------------------------------------------------
# POST/DELETE /tasks/{task_id}/tags/{tag_id}
# ---------------------------------------------------------------------------

class TestTaskTagAssignment:
    def _setup(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        gid = create_group(client, h, pid)
        task_id = create_task(client, h, gid)
        tag_id = create_tag(client, h, pid).json()["id"]
        return h, pid, gid, task_id, tag_id

    def test_assign_returns_204(self, client, auth):
        h, pid, gid, tid, tag_id = self._setup(client, auth)
        assert client.post(f"/tasks/{tid}/tags/{tag_id}", headers=h).status_code == 204

    def test_tag_appears_in_task_response(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        gid = create_group(client, h, pid)
        tid = create_task(client, h, gid)
        tag_id = create_tag(client, h, pid, name="Urgente", color="#EF4444").json()["id"]
        client.post(f"/tasks/{tid}/tags/{tag_id}", headers=h)
        assert any(t["id"] == tag_id for t in client.get(f"/tasks/{tid}", headers=h).json()["tags"])

    def test_assign_is_idempotent(self, client, auth):
        h, pid, gid, tid, tag_id = self._setup(client, auth)
        client.post(f"/tasks/{tid}/tags/{tag_id}", headers=h)
        assert client.post(f"/tasks/{tid}/tags/{tag_id}", headers=h).status_code == 204
        assert len(client.get(f"/tasks/{tid}", headers=h).json()["tags"]) == 1

    def test_assign_task_not_found_returns_404(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        tag_id = create_tag(client, h, pid).json()["id"]
        assert client.post(f"/tasks/9999/tags/{tag_id}", headers=h).status_code == 404

    def test_assign_tag_not_found_returns_404(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        gid = create_group(client, h, pid)
        tid = create_task(client, h, gid)
        assert client.post(f"/tasks/{tid}/tags/9999", headers=h).status_code == 404

    def test_cross_project_tag_assignment_returns_422(self, client, auth):
        user, h = auth
        pid1 = create_project(client, h, name="P1")
        pid2 = create_project(client, h, name="P2")
        gid = create_group(client, h, pid1)
        tid = create_task(client, h, gid)
        tag_id = create_tag(client, h, pid2, name="OtherProject").json()["id"]
        assert client.post(f"/tasks/{tid}/tags/{tag_id}", headers=h).status_code == 422

    def test_unassign_removes_tag(self, client, auth):
        h, pid, gid, tid, tag_id = self._setup(client, auth)
        client.post(f"/tasks/{tid}/tags/{tag_id}", headers=h)
        client.delete(f"/tasks/{tid}/tags/{tag_id}", headers=h)
        assert client.get(f"/tasks/{tid}", headers=h).json()["tags"] == []

    def test_unassign_task_not_found_returns_404(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        tag_id = create_tag(client, h, pid).json()["id"]
        assert client.delete(f"/tasks/9999/tags/{tag_id}", headers=h).status_code == 404


# ---------------------------------------------------------------------------
# POST/DELETE /groups/{group_id}/tags/{tag_id}
# ---------------------------------------------------------------------------

class TestGroupTagAssignment:
    def _setup(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        gid = create_group(client, h, pid)
        tag_id = create_tag(client, h, pid).json()["id"]
        return h, pid, gid, tag_id

    def test_assign_returns_204(self, client, auth):
        h, pid, gid, tag_id = self._setup(client, auth)
        assert client.post(f"/groups/{gid}/tags/{tag_id}", headers=h).status_code == 204

    def test_tag_appears_in_group_response(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        gid = create_group(client, h, pid)
        tag_id = create_tag(client, h, pid, name="Sprint").json()["id"]
        client.post(f"/groups/{gid}/tags/{tag_id}", headers=h)
        assert any(t["id"] == tag_id for t in client.get(f"/groups/{gid}", headers=h).json()["tags"])

    def test_assign_is_idempotent(self, client, auth):
        h, pid, gid, tag_id = self._setup(client, auth)
        client.post(f"/groups/{gid}/tags/{tag_id}", headers=h)
        assert client.post(f"/groups/{gid}/tags/{tag_id}", headers=h).status_code == 204
        assert len(client.get(f"/groups/{gid}", headers=h).json()["tags"]) == 1

    def test_assign_group_not_found_returns_404(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        tag_id = create_tag(client, h, pid).json()["id"]
        assert client.post(f"/groups/9999/tags/{tag_id}", headers=h).status_code == 404

    def test_assign_tag_not_found_returns_404(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        gid = create_group(client, h, pid)
        assert client.post(f"/groups/{gid}/tags/9999", headers=h).status_code == 404

    def test_cross_project_tag_assignment_returns_422(self, client, auth):
        user, h = auth
        pid1 = create_project(client, h, name="P1")
        pid2 = create_project(client, h, name="P2")
        gid = create_group(client, h, pid1)
        tag_id = create_tag(client, h, pid2, name="OtherProject").json()["id"]
        assert client.post(f"/groups/{gid}/tags/{tag_id}", headers=h).status_code == 422

    def test_unassign_removes_tag(self, client, auth):
        h, pid, gid, tag_id = self._setup(client, auth)
        client.post(f"/groups/{gid}/tags/{tag_id}", headers=h)
        client.delete(f"/groups/{gid}/tags/{tag_id}", headers=h)
        assert client.get(f"/groups/{gid}", headers=h).json()["tags"] == []

    def test_unassign_group_not_found_returns_404(self, client, auth):
        user, h = auth
        pid = create_project(client, h)
        tag_id = create_tag(client, h, pid).json()["id"]
        assert client.delete(f"/groups/9999/tags/{tag_id}", headers=h).status_code == 404
