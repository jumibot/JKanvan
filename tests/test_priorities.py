from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_project(client: TestClient, headers, name="Test Project"):
    return client.post("/projects/", json={"name": name}, headers=headers).json()["id"]


def add_member(client: TestClient, headers, project_id: int, user_id: int):
    client.post(f"/projects/{project_id}/members/{user_id}", headers=headers)


def register_and_login(client: TestClient, email: str, password: str = "pass1234"):
    """Returns (headers, user_id)."""
    r = client.post("/users/", json={"name": "User", "email": email, "password": password})
    user_id = r.json()["id"]
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, user_id


def _create(client, headers, project_id, name="Urgent", icon="flag", color="#EF4444"):
    return client.post(
        f"/projects/{project_id}/priorities/",
        json={"name": name, "icon": icon, "color": color},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# POST /projects/{project_id}/priorities/
# ---------------------------------------------------------------------------

class TestCreatePriority:
    def test_creates_priority_returns_201(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        assert _create(client, h, pid).status_code == 201

    def test_response_has_correct_fields(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        data = _create(client, h, pid).json()
        assert data["name"] == "Urgent"
        assert data["icon"] == "flag"
        assert data["color"] == "#EF4444"
        assert data["project_id"] == pid
        assert "id" in data

    def test_color_is_uppercased(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        assert _create(client, h, pid, color="#ef4444").json()["color"] == "#EF4444"

    def test_duplicate_name_in_same_project_returns_409(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        _create(client, h, pid, name="High")
        assert _create(client, h, pid, name="High").status_code == 409

    def test_duplicate_name_in_different_project_is_allowed(self, client: TestClient, auth):
        _, h = auth
        pid1 = create_project(client, h, name="P1")
        pid2 = create_project(client, h, name="P2")
        _create(client, h, pid1, name="Critical")
        assert _create(client, h, pid2, name="Critical").status_code == 201

    def test_invalid_color_returns_422(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        assert client.post(
            f"/projects/{pid}/priorities/",
            json={"name": "Bad", "icon": "flag", "color": "red"},
            headers=h,
        ).status_code == 422

    def test_missing_name_returns_422(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        assert client.post(
            f"/projects/{pid}/priorities/",
            json={"icon": "flag", "color": "#EF4444"},
            headers=h,
        ).status_code == 422

    def test_unauthenticated_returns_401(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        assert client.post(
            f"/projects/{pid}/priorities/",
            json={"name": "X", "icon": "flag", "color": "#EF4444"},
        ).status_code == 401

    def test_member_cannot_create_priority_returns_403(self, client: TestClient, auth):
        _, h_owner = auth
        pid = create_project(client, h_owner)
        h_member, member_id = register_and_login(client, "mem1@test.com")
        add_member(client, h_owner, pid, member_id)
        assert _create(client, h_member, pid).status_code == 403

    def test_non_member_cannot_create_priority_returns_403(self, client: TestClient, auth):
        _, h_owner = auth
        pid = create_project(client, h_owner)
        h_other, _ = register_and_login(client, "other@test.com")
        assert _create(client, h_other, pid).status_code == 403


# ---------------------------------------------------------------------------
# GET /projects/{project_id}/priorities/  and  /{priority_id}
# ---------------------------------------------------------------------------

class TestListPriorities:
    def test_empty_list(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        assert client.get(f"/projects/{pid}/priorities/", headers=h).json() == []

    def test_returns_project_priorities_only(self, client: TestClient, auth):
        _, h = auth
        pid1 = create_project(client, h, name="P1")
        pid2 = create_project(client, h, name="P2")
        _create(client, h, pid1, name="High")
        _create(client, h, pid1, name="Low")
        _create(client, h, pid2, name="Critical")
        items = client.get(f"/projects/{pid1}/priorities/", headers=h).json()
        assert len(items) == 2
        assert all(p["project_id"] == pid1 for p in items)

    def test_ordered_by_id(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        _create(client, h, pid, name="High")
        _create(client, h, pid, name="Low")
        names = [p["name"] for p in client.get(f"/projects/{pid}/priorities/", headers=h).json()]
        assert names == ["High", "Low"]

    def test_member_can_list_priorities(self, client: TestClient, auth):
        _, h_owner = auth
        pid = create_project(client, h_owner)
        _create(client, h_owner, pid, name="Normal")
        h_member, member_id = register_and_login(client, "viewer@test.com")
        add_member(client, h_owner, pid, member_id)
        assert len(client.get(f"/projects/{pid}/priorities/", headers=h_member).json()) == 1

    def test_non_member_cannot_list_returns_403(self, client: TestClient, auth):
        _, h_owner = auth
        pid = create_project(client, h_owner)
        h_other, _ = register_and_login(client, "outsider@test.com")
        assert client.get(f"/projects/{pid}/priorities/", headers=h_other).status_code == 403

    def test_unauthenticated_returns_401(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        assert client.get(f"/projects/{pid}/priorities/").status_code == 401


class TestGetPriority:
    def test_returns_existing(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        prio_id = _create(client, h, pid).json()["id"]
        assert client.get(f"/projects/{pid}/priorities/{prio_id}", headers=h).json()["name"] == "Urgent"

    def test_not_found_returns_404(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        assert client.get(f"/projects/{pid}/priorities/999", headers=h).status_code == 404

    def test_priority_from_other_project_returns_404(self, client: TestClient, auth):
        _, h = auth
        pid1 = create_project(client, h, name="P1")
        pid2 = create_project(client, h, name="P2")
        prio_id = _create(client, h, pid1).json()["id"]
        assert client.get(f"/projects/{pid2}/priorities/{prio_id}", headers=h).status_code == 404


# ---------------------------------------------------------------------------
# PATCH /projects/{project_id}/priorities/{priority_id}
# ---------------------------------------------------------------------------

class TestUpdatePriority:
    def test_update_name(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        prio_id = _create(client, h, pid).json()["id"]
        assert client.patch(
            f"/projects/{pid}/priorities/{prio_id}", json={"name": "Critical"}, headers=h
        ).json()["name"] == "Critical"

    def test_update_color(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        prio_id = _create(client, h, pid).json()["id"]
        assert client.patch(
            f"/projects/{pid}/priorities/{prio_id}", json={"color": "#3B82F6"}, headers=h
        ).json()["color"] == "#3B82F6"

    def test_update_icon(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        prio_id = _create(client, h, pid).json()["id"]
        assert client.patch(
            f"/projects/{pid}/priorities/{prio_id}", json={"icon": "emergency"}, headers=h
        ).json()["icon"] == "emergency"

    def test_duplicate_name_returns_409(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        _create(client, h, pid, name="High")
        prio_id = _create(client, h, pid, name="Low").json()["id"]
        assert client.patch(
            f"/projects/{pid}/priorities/{prio_id}", json={"name": "High"}, headers=h
        ).status_code == 409

    def test_not_found_returns_404(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        assert client.patch(
            f"/projects/{pid}/priorities/999", json={"name": "X"}, headers=h
        ).status_code == 404

    def test_empty_body_returns_422(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        prio_id = _create(client, h, pid).json()["id"]
        assert client.patch(
            f"/projects/{pid}/priorities/{prio_id}", json={}, headers=h
        ).status_code == 422

    def test_member_cannot_update_returns_403(self, client: TestClient, auth):
        _, h_owner = auth
        pid = create_project(client, h_owner)
        prio_id = _create(client, h_owner, pid).json()["id"]
        h_member, member_id = register_and_login(client, "mem2@test.com")
        add_member(client, h_owner, pid, member_id)
        assert client.patch(
            f"/projects/{pid}/priorities/{prio_id}", json={"name": "Hacked"}, headers=h_member
        ).status_code == 403


# ---------------------------------------------------------------------------
# DELETE /projects/{project_id}/priorities/{priority_id}
# ---------------------------------------------------------------------------

class TestDeletePriority:
    def test_delete_returns_204(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        prio_id = _create(client, h, pid).json()["id"]
        assert client.delete(f"/projects/{pid}/priorities/{prio_id}", headers=h).status_code == 204

    def test_deleted_not_found(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        prio_id = _create(client, h, pid).json()["id"]
        client.delete(f"/projects/{pid}/priorities/{prio_id}", headers=h)
        assert client.get(f"/projects/{pid}/priorities/{prio_id}", headers=h).status_code == 404

    def test_not_found_returns_404(self, client: TestClient, auth):
        _, h = auth
        pid = create_project(client, h)
        assert client.delete(f"/projects/{pid}/priorities/999", headers=h).status_code == 404

    def test_member_cannot_delete_returns_403(self, client: TestClient, auth):
        _, h_owner = auth
        pid = create_project(client, h_owner)
        prio_id = _create(client, h_owner, pid).json()["id"]
        h_member, member_id = register_and_login(client, "mem3@test.com")
        add_member(client, h_owner, pid, member_id)
        assert client.delete(
            f"/projects/{pid}/priorities/{prio_id}", headers=h_member
        ).status_code == 403
