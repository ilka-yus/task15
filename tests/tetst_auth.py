import pytest

@pytest.mark.asyncio
async def test_register(client):
    response = await client.post("/register", json={
        "username": "ilnara",
        "password": "password12345"
    })
    assert response.status_code == 200
    assert response.json()["username"] == "ilnara"
    
    response = await client.post("/register", json={
        "username": "ilnara",
        "password": "password"
    })
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_login(client):
    response = await client.post("/login", json={
        "username": "ilnara",
        "password": "password12345"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
    
    response = await client.post("/login", json={
        "username": "ilnara",
        "password": "password"
    })
    assert response.status_code == 401