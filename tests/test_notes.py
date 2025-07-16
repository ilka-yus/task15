import pytest

@pytest.mark.asyncio
async def test_notes_crud(client):
    await client.post("/register", json={
        "username": "ilnara",
        "password": "password12345"
    })
    login = await client.post("/login", json={
        "username": "ilnara",
        "password": "password12345"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    note_data = {"text": "Note 1"}
    response = await client.post("/notes", headers=headers, json=note_data)
    assert response.status_code == 200
    note_id = response.json()["id"]
    
    response = await client.get("/notes", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = await client.delete(f"/notes/{note_id}", headers=headers)
    assert response.status_code == 200

    response = await client.delete(f"/notes/{note_id}", headers=headers)
    assert response.status_code == 404