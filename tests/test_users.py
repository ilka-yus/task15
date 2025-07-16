import pytest

@pytest.mark.asyncio
async def test_users_me(client):
    await client.post("/register", json={
        "username": "ilnara",
        "password": "password12345"
    })

    login = await client.post("/login", json={
        "username": "ilnara",
        "password": "password12345"
    })
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = await client.get("/users/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "ilnara"