import pytest
from fastapi.testclient import TestClient


# ── helpers ──────────────────────────────────────────────────────────────────

def create_user(client, name="Alice", email="alice@test.com", password="secret123"):
    return client.post("/users/", json={"name": name, "email": email, "password": password}).json()["id"]


def login(client, email: str, password: str = "secret123") -> dict:
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def create_priority(client, headers):
    """Creates a scratch project, adds a priority to it, and returns the priority id."""
    proj_id = client.post("/projects/", json={"name": "_prio_proj"}, headers=headers).json()["id"]
    return client.post(f"/projects/{proj_id}/priorities/", json={
        "name": "High", "icon": "arrow_upward", "color": "#F97316"
    }, headers=headers).json()["id"]


def create_project(client, headers, name="My Project", **kwargs):
    payload = {"name": name, "icon": "rocket_launch", "color": "#3B82F6"}
    payload.update(kwargs)
    return client.post("/projects/", json=payload, headers=headers)


# ── Create ────────────────────────────────────────────────────────────────────

class TestCreateProject:
    def test_unauthenticated_returns_401(self, client):
        assert client.post("/projects/", json={"name": "X"}).status_code == 401

    def test_creates_project_returns_201(self, client, auth):
        _, h = auth
        assert create_project(client, h).status_code == 201

    def test_response_has_correct_fields(self, client, auth):
        user, h = auth
        data = create_project(client, h, name="Alpha").json()
        assert data["name"] == "Alpha"
        assert data["icon"] == "rocket_launch"
        assert data["color"] == "#3B82F6"
        assert data["owner"]["id"] == user["id"]
        assert data["leader"]["id"] == user["id"]
        assert data["priority"] is None
        assert data["members"] == []
        assert "id" in data
        assert "created_at" in data

    def test_leader_defaults_to_owner(self, client, auth):
        user, h = auth
        data = create_project(client, h).json()
        assert data["leader"]["id"] == user["id"]

    def test_with_leader(self, client, auth):
        _, h = auth
        lid = create_user(client, name="Leader", email="leader@test.com")
        assert create_project(client, h, leader_id=lid).json()["leader"]["id"] == lid

    def test_with_priority(self, client, auth):
        _, h = auth
        pid = create_priority(client, h)
        assert create_project(client, h, priority_id=pid).json()["priority"]["id"] == pid

    def test_invalid_leader_returns_404(self, client, auth):
        _, h = auth
        assert create_project(client, h, leader_id=9999).status_code == 404

    def test_invalid_priority_returns_404(self, client, auth):
        _, h = auth
        assert create_project(client, h, priority_id=9999).status_code == 404

    def test_missing_name_returns_422(self, client, auth):
        _, h = auth
        assert client.post("/projects/", json={"icon": "folder", "color": "#3B82F6"}, headers=h).status_code == 422

    def test_description_optional(self, client, auth):
        _, h = auth
        assert create_project(client, h).json()["description"] is None


# ── List / Get ────────────────────────────────────────────────────────────────

class TestListProjects:
    def test_unauthenticated_returns_401(self, client):
        assert client.get("/projects/").status_code == 401

    def test_empty_list(self, client, auth):
        _, h = auth
        assert client.get("/projects/", headers=h).json() == []

    def test_returns_all(self, client, auth):
        _, h = auth
        create_project(client, h, name="Alpha")
        create_project(client, h, name="Beta")
        assert len(client.get("/projects/", headers=h).json()) == 2

    def test_ordered_by_id(self, client, auth):
        _, h = auth
        create_project(client, h, name="Alpha")
        create_project(client, h, name="Beta")
        names = [p["name"] for p in client.get("/projects/", headers=h).json()]
        assert names == ["Alpha", "Beta"]


class TestGetProject:
    def test_returns_existing(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h, name="Alpha").json()["id"]
        assert client.get(f"/projects/{proj_id}", headers=h).json()["name"] == "Alpha"

    def test_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.get("/projects/999", headers=h).status_code == 404


# ── Get Groups ────────────────────────────────────────────────────────────────

class TestGetProjectGroups:
    def test_empty_groups(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        assert client.get(f"/projects/{proj_id}/groups", headers=h).json() == []

    def test_returns_only_groups_of_project(self, client, auth):
        _, h = auth
        proj1 = create_project(client, h, name="P1").json()["id"]
        proj2 = create_project(client, h, name="P2").json()["id"]
        client.post("/groups/", json={"name": "G1", "color": "#3B82F6", "project_id": proj1}, headers=h)
        client.post("/groups/", json={"name": "G2", "color": "#3B82F6", "project_id": proj1}, headers=h)
        client.post("/groups/", json={"name": "G3", "color": "#3B82F6", "project_id": proj2}, headers=h)
        names = sorted(g["name"] for g in client.get(f"/projects/{proj1}/groups", headers=h).json())
        assert names == ["G1", "G2"]

    def test_project_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.get("/projects/999/groups", headers=h).status_code == 404


# ── Members ───────────────────────────────────────────────────────────────────

class TestProjectMembers:
    def test_empty_members(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        assert client.get(f"/projects/{proj_id}/members", headers=h).json() == []

    def test_add_member_returns_204(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        mid = create_user(client, name="Bob", email="bob@test.com")
        assert client.post(f"/projects/{proj_id}/members/{mid}", headers=h).status_code == 204

    def test_list_members_after_add(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        m1 = create_user(client, name="Bob", email="bob@test.com")
        m2 = create_user(client, name="Carol", email="carol@test.com")
        client.post(f"/projects/{proj_id}/members/{m1}", headers=h)
        client.post(f"/projects/{proj_id}/members/{m2}", headers=h)
        ids = [u["id"] for u in client.get(f"/projects/{proj_id}/members", headers=h).json()]
        assert sorted(ids) == sorted([m1, m2])

    def test_add_duplicate_member_returns_409(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        mid = create_user(client, name="Bob", email="bob@test.com")
        client.post(f"/projects/{proj_id}/members/{mid}", headers=h)
        assert client.post(f"/projects/{proj_id}/members/{mid}", headers=h).status_code == 409

    def test_add_invalid_user_returns_404(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        assert client.post(f"/projects/{proj_id}/members/9999", headers=h).status_code == 404

    def test_remove_member_returns_204(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        mid = create_user(client, name="Bob", email="bob@test.com")
        client.post(f"/projects/{proj_id}/members/{mid}", headers=h)
        assert client.delete(f"/projects/{proj_id}/members/{mid}", headers=h).status_code == 204

    def test_remove_member_not_in_project_returns_404(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        mid = create_user(client, name="Bob", email="bob@test.com")
        assert client.delete(f"/projects/{proj_id}/members/{mid}", headers=h).status_code == 404

    def test_members_appear_in_project_response(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        mid = create_user(client, name="Bob", email="bob@test.com")
        client.post(f"/projects/{proj_id}/members/{mid}", headers=h)
        assert any(m["id"] == mid for m in client.get(f"/projects/{proj_id}", headers=h).json()["members"])

    def test_member_cannot_add_members_returns_403(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        # Create a plain member and log in as them
        mid = create_user(client, name="Member", email="member@test.com")
        client.post(f"/projects/{proj_id}/members/{mid}", headers=h)
        member_h = login(client, "member@test.com")
        stranger_id = create_user(client, name="Stranger", email="stranger@test.com")
        assert client.post(f"/projects/{proj_id}/members/{stranger_id}", headers=member_h).status_code == 403


# ── Update ────────────────────────────────────────────────────────────────────

class TestUpdateProject:
    def test_update_name(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        assert client.patch(f"/projects/{proj_id}", json={"name": "Renamed"}, headers=h).json()["name"] == "Renamed"

    def test_update_sets_modified_at(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        assert client.patch(f"/projects/{proj_id}", json={"name": "New"}, headers=h).json()["modified_at"] is not None

    def test_update_leader(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        lid = create_user(client, name="Lead", email="lead@test.com")
        assert client.patch(f"/projects/{proj_id}", json={"leader_id": lid}, headers=h).json()["leader"]["id"] == lid

    def test_update_owner(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        new_owner_id = create_user(client, name="New Owner", email="owner2@test.com")
        assert client.patch(f"/projects/{proj_id}", json={"owner_id": new_owner_id}, headers=h).json()["owner"]["id"] == new_owner_id

    def test_update_priority(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        pid = create_priority(client, h)
        assert client.patch(f"/projects/{proj_id}", json={"priority_id": pid}, headers=h).json()["priority"]["id"] == pid

    def test_invalid_leader_returns_404(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        assert client.patch(f"/projects/{proj_id}", json={"leader_id": 999}, headers=h).status_code == 404

    def test_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.patch("/projects/999", json={"name": "X"}, headers=h).status_code == 404

    def test_non_member_cannot_update_returns_403(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        other_id = create_user(client, name="Other", email="other@test.com")
        other_h = login(client, "other@test.com")
        assert client.patch(f"/projects/{proj_id}", json={"name": "Hack"}, headers=other_h).status_code == 403

    def test_leader_can_update(self, client, auth):
        _, h = auth
        lid = create_user(client, name="Leader", email="leader@test.com")
        proj_id = create_project(client, h, leader_id=lid).json()["id"]
        leader_h = login(client, "leader@test.com")
        assert client.patch(f"/projects/{proj_id}", json={"name": "Leader Updated"}, headers=leader_h).status_code == 200

    def test_leader_cannot_be_null_returns_422(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        assert client.patch(f"/projects/{proj_id}", json={"leader_id": None}, headers=h).status_code == 422


# ── Delete ────────────────────────────────────────────────────────────────────

class TestDeleteProject:
    def test_delete_empty_project_returns_204(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        assert client.delete(f"/projects/{proj_id}", headers=h).status_code == 204

    def test_deleted_not_found(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        client.delete(f"/projects/{proj_id}", headers=h)
        assert client.get(f"/projects/{proj_id}", headers=h).status_code == 404

    def test_delete_project_with_groups_returns_409(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        client.post("/groups/", json={"name": "G1", "color": "#3B82F6", "project_id": proj_id}, headers=h)
        assert client.delete(f"/projects/{proj_id}", headers=h).status_code == 409

    def test_409_message_mentions_groups(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        client.post("/groups/", json={"name": "G1", "color": "#3B82F6", "project_id": proj_id}, headers=h)
        assert "group" in client.delete(f"/projects/{proj_id}", headers=h).json()["detail"].lower()

    def test_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.delete("/projects/999", headers=h).status_code == 404

    def test_non_owner_cannot_delete_returns_403(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        other_id = create_user(client, name="Other", email="other@test.com")
        other_h = login(client, "other@test.com")
        assert client.delete(f"/projects/{proj_id}", headers=other_h).status_code == 403

    def test_leader_cannot_delete_returns_403(self, client, auth):
        _, h = auth
        lid = create_user(client, name="Leader", email="leader@test.com")
        proj_id = create_project(client, h, leader_id=lid).json()["id"]
        leader_h = login(client, "leader@test.com")
        assert client.delete(f"/projects/{proj_id}", headers=leader_h).status_code == 403


# ── Cascade Delete ────────────────────────────────────────────────────────────

class TestCascadeDeleteProject:
    PASSWORD = "authpass123"

    def _cascade(self, client, headers, project_id, password=None):
        pw = password if password is not None else self.PASSWORD
        return client.request(
            "DELETE", f"/projects/{project_id}/cascade",
            json={"owner_password": pw}, headers=headers,
        )

    def test_requires_auth(self, client):
        assert client.request(
            "DELETE", "/projects/1/cascade", json={"owner_password": "x"}
        ).status_code == 401

    def test_not_found_returns_404(self, client, auth):
        _, h = auth
        assert self._cascade(client, h, 9999).status_code == 404

    def test_non_owner_returns_403(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        other_id = create_user(client, name="Other", email="other@test.com")
        other_h = login(client, "other@test.com")
        assert self._cascade(client, other_h, proj_id).status_code == 403

    def test_leader_cannot_cascade_delete(self, client, auth):
        _, h = auth
        lid = create_user(client, name="Leader", email="leader@test.com")
        proj_id = create_project(client, h, leader_id=lid).json()["id"]
        leader_h = login(client, "leader@test.com")
        assert self._cascade(client, leader_h, proj_id).status_code == 403

    def test_wrong_password_returns_403(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        assert self._cascade(client, h, proj_id, password="wrongpass").status_code == 403

    def test_deletes_empty_project(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        assert self._cascade(client, h, proj_id).status_code == 204
        assert client.get(f"/projects/{proj_id}", headers=h).status_code == 404

    def test_deletes_project_with_groups_and_tasks(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        gid = client.post(
            "/groups/", json={"name": "G", "color": "#3B82F6", "project_id": proj_id}, headers=h
        ).json()["id"]
        client.post("/tasks/", json={"title": "T", "group_id": gid}, headers=h)
        assert self._cascade(client, h, proj_id).status_code == 204
        assert client.get(f"/projects/{proj_id}", headers=h).status_code == 404

    def test_cascade_removes_groups(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        gid = client.post(
            "/groups/", json={"name": "G", "color": "#3B82F6", "project_id": proj_id}, headers=h
        ).json()["id"]
        self._cascade(client, h, proj_id)
        assert client.get(f"/groups/{gid}", headers=h).status_code == 404

    def test_other_projects_unaffected(self, client, auth):
        _, h = auth
        proj_a = create_project(client, h, name="A").json()["id"]
        proj_b = create_project(client, h, name="B").json()["id"]
        self._cascade(client, h, proj_a)
        assert client.get(f"/projects/{proj_b}", headers=h).status_code == 200
