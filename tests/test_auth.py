from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_user(client: TestClient, name="Alice", email="alice@test.com", password="secret123"):
    return client.post("/users/", json={"name": name, "email": email, "password": password})


def create_project(client: TestClient, headers, name="Proj"):
    return client.post("/projects/", json={"name": name}, headers=headers)


def login(client: TestClient, email="alice@test.com", password="secret123") -> dict:
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_login_success_returns_200(self, client):
        create_user(client)
        assert client.post("/auth/login", json={"email": "alice@test.com", "password": "secret123"}).status_code == 200

    def test_login_returns_token_and_user(self, client):
        create_user(client, name="Alice")
        body = client.post("/auth/login", json={"email": "alice@test.com", "password": "secret123"}).json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["user"]["name"] == "Alice"
        assert body["user"]["email"] == "alice@test.com"
        assert "password" not in body["user"]
        assert "password_hash" not in body["user"]

    def test_login_email_case_insensitive(self, client):
        create_user(client)
        assert client.post("/auth/login", json={"email": "ALICE@TEST.COM", "password": "secret123"}).status_code == 200

    def test_login_wrong_password_returns_401(self, client):
        create_user(client)
        assert client.post("/auth/login", json={"email": "alice@test.com", "password": "wrongpass"}).status_code == 401

    def test_login_nonexistent_user_returns_401(self, client):
        assert client.post("/auth/login", json={"email": "ghost@test.com", "password": "secret123"}).status_code == 401

    def test_login_empty_password_returns_422(self, client):
        assert client.post("/auth/login", json={"email": "alice@test.com", "password": ""}).status_code == 422

    def test_token_allows_access_to_protected_endpoint(self, client):
        create_user(client)
        h = login(client)
        assert client.get("/users/", headers=h).status_code == 200

    def test_invalid_token_returns_401(self, client):
        assert client.get("/users/", headers={"Authorization": "Bearer invalid.token.here"}).status_code == 401

    def test_missing_token_returns_401(self, client):
        assert client.get("/users/").status_code == 401


# ---------------------------------------------------------------------------
# GET /users/{user_id}/projects
# ---------------------------------------------------------------------------

class TestUserProjects:
    def test_returns_empty_list_when_no_projects(self, client, auth):
        user, h = auth
        assert client.get(f"/users/{user['id']}/projects", headers=h).json() == []

    def test_returns_projects_with_owner_role(self, client, auth):
        user, h = auth
        create_project(client, h, name="MyProject")
        body = client.get(f"/users/{user['id']}/projects", headers=h).json()
        assert len(body) == 1
        assert body[0]["name"] == "MyProject"
        assert body[0]["role"] == "owner"

    def test_returns_projects_with_leader_role(self, client, auth):
        user, h = auth
        owner_id = create_user(client, name="Owner", email="owner@test.com").json()["id"]
        owner_h = {"Authorization": f"Bearer {client.post('/auth/login', json={'email': 'owner@test.com', 'password': 'secret123'}).json()['access_token']}"}
        client.post("/projects/", json={"name": "P", "leader_id": user["id"]}, headers=owner_h)
        body = client.get(f"/users/{user['id']}/projects", headers=h).json()
        assert any(p["role"] == "leader" for p in body)

    def test_returns_projects_with_member_role(self, client, auth):
        user, h = auth
        owner_id = create_user(client, name="Owner", email="owner@test.com").json()["id"]
        owner_h = {"Authorization": f"Bearer {client.post('/auth/login', json={'email': 'owner@test.com', 'password': 'secret123'}).json()['access_token']}"}
        proj_id = create_project(client, owner_h).json()["id"]
        client.post(f"/projects/{proj_id}/members/{user['id']}", headers=owner_h)
        body = client.get(f"/users/{user['id']}/projects", headers=h).json()
        assert any(p["role"] == "member" for p in body)

    def test_returns_multiple_projects(self, client, auth):
        user, h = auth
        create_project(client, h, name="P1")
        create_project(client, h, name="P2")
        assert len(client.get(f"/users/{user['id']}/projects", headers=h).json()) == 2

    def test_nonexistent_user_returns_404(self, client, auth):
        _, h = auth
        assert client.get("/users/9999/projects", headers=h).status_code == 404

    def test_response_includes_role_field(self, client, auth):
        user, h = auth
        create_project(client, h, name="FieldCheck")
        body = client.get(f"/users/{user['id']}/projects", headers=h).json()
        assert "role" in body[0]


# ---------------------------------------------------------------------------
# GET /projects/{project_id}/role/{user_id}
# ---------------------------------------------------------------------------

class TestProjectUserRole:
    def test_owner_role(self, client, auth):
        user, h = auth
        proj_id = create_project(client, h).json()["id"]
        assert client.get(f"/projects/{proj_id}/role/{user['id']}", headers=h).json()["role"] == "owner"

    def test_leader_role(self, client, auth):
        _, h = auth
        leader_id = create_user(client, name="Leader", email="leader@test.com").json()["id"]
        proj_id = client.post("/projects/", json={"name": "P", "leader_id": leader_id}, headers=h).json()["id"]
        assert client.get(f"/projects/{proj_id}/role/{leader_id}", headers=h).json()["role"] == "leader"

    def test_member_role(self, client, auth):
        _, h = auth
        proj_id = create_project(client, h).json()["id"]
        mid = create_user(client, name="Member", email="member@test.com").json()["id"]
        client.post(f"/projects/{proj_id}/members/{mid}", headers=h)
        assert client.get(f"/projects/{proj_id}/role/{mid}", headers=h).json()["role"] == "member"

    def test_user_not_in_project_returns_404(self, client, auth):
        user, h = auth
        proj_id = create_project(client, h).json()["id"]
        other_id = create_user(client, name="Other", email="other@test.com").json()["id"]
        assert client.get(f"/projects/{proj_id}/role/{other_id}", headers=h).status_code == 404

    def test_nonexistent_project_returns_404(self, client, auth):
        user, h = auth
        assert client.get(f"/projects/9999/role/{user['id']}", headers=h).status_code == 404
