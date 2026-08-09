"""Auth API tests."""
def test_register(client):
    resp = client.post("/api/auth/register", json={
        "email": "new@nexa.io", "password": "test1234", "name": "New User"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "new@nexa.io"
    assert "token" in data


def test_register_duplicate(client):
    client.post("/api/auth/register", json={
        "email": "dup@nexa.io", "password": "test1234", "name": "Dup"
    })
    resp = client.post("/api/auth/register", json={
        "email": "dup@nexa.io", "password": "test1234", "name": "Dup2"
    })
    assert resp.status_code == 400


def test_login(client):
    client.post("/api/auth/register", json={
        "email": "login@nexa.io", "password": "test1234", "name": "Login"
    })
    resp = client.post("/api/auth/login", json={
        "email": "login@nexa.io", "password": "test1234"
    })
    assert resp.status_code == 200
    assert "token" in resp.json()


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={
        "email": "wrong@nexa.io", "password": "test1234", "name": "Wrong"
    })
    resp = client.post("/api/auth/login", json={
        "email": "wrong@nexa.io", "password": "badpass"
    })
    assert resp.status_code == 401


def test_protected_route_without_token(client):
    resp = client.get("/api/projects")
    assert resp.status_code in (401, 403)
