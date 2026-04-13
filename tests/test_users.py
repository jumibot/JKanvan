from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_user(client: TestClient, name="Alice", email="alice@test.com",
                password="secret123", avatar_url=None):
    payload = {"name": name, "email": email, "password": password}
    if avatar_url:
        payload["avatar_url"] = avatar_url
    return client.post("/users/", json=payload)


def login(client: TestClient, email: str, password: str) -> dict:
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------------------
# POST /users/  (public)
# ---------------------------------------------------------------------------

class TestCreateUser:
    def test_creates_user_returns_201(self, client):
        assert create_user(client).status_code == 201

    def test_response_has_correct_fields(self, client):
        body = create_user(client, name="Bob Chen", email="bob@test.com",
                           avatar_url="https://example.com/bob.jpg").json()
        assert body["name"] == "Bob Chen"
        assert body["email"] == "bob@test.com"
        assert body["avatar_url"] == "https://example.com/bob.jpg"
        assert "id" in body
        assert "created_at" in body
        assert "password" not in body
        assert "password_hash" not in body

    def test_email_is_lowercased(self, client):
        assert create_user(client, email="ALICE@TEST.COM").json()["email"] == "alice@test.com"

    def test_avatar_url_optional(self, client):
        assert create_user(client).json()["avatar_url"] is None

    def test_duplicate_email_returns_409(self, client):
        create_user(client, email="dup@test.com")
        assert create_user(client, name="Other", email="dup@test.com").status_code == 409

    def test_invalid_email_returns_422(self, client):
        assert client.post("/users/", json={"name": "Bad", "email": "notanemail", "password": "secret123"}).status_code == 422

    def test_empty_name_returns_422(self, client):
        assert client.post("/users/", json={"name": "", "email": "x@test.com", "password": "secret123"}).status_code == 422

    def test_missing_email_returns_422(self, client):
        assert client.post("/users/", json={"name": "No email", "password": "secret123"}).status_code == 422

    def test_missing_password_returns_422(self, client):
        assert client.post("/users/", json={"name": "No pass", "email": "x@test.com"}).status_code == 422

    def test_short_password_returns_422(self, client):
        assert client.post("/users/", json={"name": "Short", "email": "x@test.com", "password": "123"}).status_code == 422


# ---------------------------------------------------------------------------
# GET /users/  (auth required)
# ---------------------------------------------------------------------------

class TestListUsers:
    def test_unauthenticated_returns_401(self, client):
        assert client.get("/users/").status_code == 401

    def test_empty_list(self, client, auth):
        _, h = auth
        # auth fixture already created one user
        assert len(client.get("/users/", headers=h).json()) == 1

    def test_returns_all(self, client, auth):
        _, h = auth
        create_user(client, name="A", email="a@test.com")
        create_user(client, name="B", email="b@test.com")
        assert len(client.get("/users/", headers=h).json()) == 3  # auth user + A + B

    def test_ordered_by_id(self, client, auth):
        _, h = auth
        create_user(client, name="First", email="first@test.com")
        create_user(client, name="Second", email="second@test.com")
        names = [u["name"] for u in client.get("/users/", headers=h).json()]
        assert "First" in names and "Second" in names

    def test_password_not_in_response(self, client, auth):
        _, h = auth
        for u in client.get("/users/", headers=h).json():
            assert "password" not in u
            assert "password_hash" not in u


# ---------------------------------------------------------------------------
# GET /users/{id}  (auth required)
# ---------------------------------------------------------------------------

class TestGetUser:
    def test_unauthenticated_returns_401(self, client):
        assert client.get("/users/1").status_code == 401

    def test_returns_existing(self, client, auth):
        _, h = auth
        uid = create_user(client, name="Find me", email="find@test.com").json()["id"]
        assert client.get(f"/users/{uid}", headers=h).json()["name"] == "Find me"

    def test_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.get("/users/9999", headers=h).status_code == 404


# ---------------------------------------------------------------------------
# PATCH /users/{id}  (self only)
# ---------------------------------------------------------------------------

class TestUpdateUser:
    def test_unauthenticated_returns_401(self, client):
        assert client.patch("/users/1", json={"name": "X"}).status_code == 401

    def test_update_name(self, client):
        r = create_user(client)
        uid = r.json()["id"]
        h = login(client, "alice@test.com", "secret123")
        assert client.patch(f"/users/{uid}", json={"name": "New"}, headers=h).json()["name"] == "New"

    def test_update_email_lowercased(self, client):
        uid = create_user(client).json()["id"]
        h = login(client, "alice@test.com", "secret123")
        assert client.patch(f"/users/{uid}", json={"email": "NEW@TEST.COM"}, headers=h).json()["email"] == "new@test.com"

    def test_update_password_does_not_expose_hash(self, client):
        uid = create_user(client).json()["id"]
        h = login(client, "alice@test.com", "secret123")
        r = client.patch(f"/users/{uid}", json={"password": "newpassword"}, headers=h)
        assert r.status_code == 200
        assert "password_hash" not in r.json()

    def test_update_sets_modified_at(self, client):
        uid = create_user(client).json()["id"]
        h = login(client, "alice@test.com", "secret123")
        assert client.patch(f"/users/{uid}", json={"name": "Updated"}, headers=h).json()["modified_at"] is not None

    def test_email_conflict_returns_409(self, client):
        create_user(client, name="Other", email="other@test.com")
        uid = create_user(client).json()["id"]
        h = login(client, "alice@test.com", "secret123")
        assert client.patch(f"/users/{uid}", json={"email": "other@test.com"}, headers=h).status_code == 409

    def test_same_email_is_ok(self, client):
        uid = create_user(client, email="keep@test.com").json()["id"]
        h = login(client, "keep@test.com", "secret123")
        assert client.patch(f"/users/{uid}", json={"email": "keep@test.com"}, headers=h).status_code == 200

    def test_other_user_returns_403(self, client, auth):
        _, h = auth  # auth user
        other_id = create_user(client, name="Other", email="other@test.com").json()["id"]
        assert client.patch(f"/users/{other_id}", json={"name": "Hack"}, headers=h).status_code == 403

    def test_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.patch("/users/9999", json={"name": "Ghost"}, headers=h).status_code == 404

    def test_empty_body_returns_422(self, client):
        uid = create_user(client).json()["id"]
        h = login(client, "alice@test.com", "secret123")
        assert client.patch(f"/users/{uid}", json={}, headers=h).status_code == 422


# ---------------------------------------------------------------------------
# DELETE /users/{id}  (self only)
# ---------------------------------------------------------------------------

class TestDeleteUser:
    def test_unauthenticated_returns_401(self, client):
        assert client.delete("/users/1").status_code == 401

    def test_delete_returns_204(self, client):
        uid = create_user(client).json()["id"]
        h = login(client, "alice@test.com", "secret123")
        assert client.delete(f"/users/{uid}", headers=h).status_code == 204

    def test_deleted_not_found(self, client, auth):
        _, h = auth
        uid = create_user(client, name="Del", email="del@test.com").json()["id"]
        hdel = login(client, "del@test.com", "secret123")
        client.delete(f"/users/{uid}", headers=hdel)
        assert client.get(f"/users/{uid}", headers=h).status_code == 404

    def test_other_user_returns_403(self, client, auth):
        _, h = auth
        other_id = create_user(client, name="Other", email="other@test.com").json()["id"]
        assert client.delete(f"/users/{other_id}", headers=h).status_code == 403

    def test_not_found_returns_404(self, client, auth):
        _, h = auth
        assert client.delete("/users/9999", headers=h).status_code == 404

    def test_cannot_delete_owner(self, client, auth):
        _, h = auth
        uid = create_user(client).json()["id"]
        howner = login(client, "alice@test.com", "secret123")
        client.post("/projects/", json={"name": "My Project", "icon": "folder", "color": "#3B82F6"}, headers=howner)
        assert client.delete(f"/users/{uid}", headers=howner).status_code == 409


# ---------------------------------------------------------------------------
# Admin operations
# ---------------------------------------------------------------------------

class TestAdminUser:
    def test_new_user_is_not_admin(self, client):
        body = create_user(client).json()
        assert body["is_admin"] is False

    def test_response_includes_is_admin_field(self, client, auth):
        _, h = auth
        users = client.get("/users/", headers=h).json()
        assert all("is_admin" in u for u in users)

    def test_admin_can_update_other_user(self, client, admin_auth):
        _, ha = admin_auth
        other_id = create_user(client, name="Other", email="other@test.com").json()["id"]
        assert client.patch(f"/users/{other_id}", json={"name": "Updated"}, headers=ha).status_code == 200

    def test_admin_can_set_is_admin(self, client, admin_auth):
        _, ha = admin_auth
        uid = create_user(client, name="Other", email="other@test.com").json()["id"]
        r = client.patch(f"/users/{uid}", json={"is_admin": True}, headers=ha)
        assert r.status_code == 200
        assert r.json()["is_admin"] is True

    def test_admin_can_revoke_is_admin(self, client, admin_auth):
        _, ha = admin_auth
        uid = create_user(client, name="Other", email="other@test.com").json()["id"]
        client.patch(f"/users/{uid}", json={"is_admin": True}, headers=ha)
        r = client.patch(f"/users/{uid}", json={"is_admin": False}, headers=ha)
        assert r.status_code == 200
        assert r.json()["is_admin"] is False

    def test_non_admin_cannot_set_is_admin_on_self(self, client):
        uid = create_user(client).json()["id"]
        h = login(client, "alice@test.com", "secret123")
        assert client.patch(f"/users/{uid}", json={"is_admin": True}, headers=h).status_code == 403

    def test_non_admin_cannot_set_is_admin_on_other(self, client, auth):
        _, h = auth
        other_id = create_user(client, name="Other", email="other@test.com").json()["id"]
        assert client.patch(f"/users/{other_id}", json={"is_admin": True}, headers=h).status_code == 403

    def test_admin_can_delete_other_user(self, client, admin_auth):
        _, ha = admin_auth
        other_id = create_user(client, name="Other", email="other@test.com").json()["id"]
        assert client.delete(f"/users/{other_id}", headers=ha).status_code == 204

    def test_admin_delete_other_then_not_found(self, client, admin_auth):
        _, ha = admin_auth
        other_id = create_user(client, name="Other", email="other@test.com").json()["id"]
        client.delete(f"/users/{other_id}", headers=ha)
        assert client.get(f"/users/{other_id}", headers=ha).status_code == 404

    def test_admin_cannot_self_revoke_admin(self, client, admin_auth):
        admin, ha = admin_auth
        assert client.patch(f"/users/{admin['id']}", json={"is_admin": False}, headers=ha).status_code == 403

    def test_admin_cannot_delete_self(self, client, admin_auth):
        admin, ha = admin_auth
        assert client.delete(f"/users/{admin['id']}", headers=ha).status_code == 403
