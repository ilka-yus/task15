from fastapi import FastAPI, HTTPException, Depends
from typing import List
from sqlalchemy.future import select
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import WebSocket, WebSocketDisconnect

from app.database import init_db, get_session, get_redis
from app.schemas import UserCreate, UserLogin, NoteCreate, NoteUpdate, NoteOut
from app.crud import create_user, create_note, get_notes_with_filters, get_note, update_note, delete_note
from app.auth_utils import get_user_by_username
from app.security import verify_password, create_access_token, require_role
from app.dependencies import get_current_user
from app.models import User, Note
from app.tasks import send_mock_email
from app.websocket_manager import ConnectionManager

import redis.asyncio as redis
import json

app = FastAPI()
manager = ConnectionManager()

async def invalidate_notes_cache(redis: redis.Redis, user_id: int):
    pattern = f"notes:{user_id}*"
    async for key in redis.scan_iter(pattern):
        await redis.delete(key)

@app.get("/")
async def root():
    return {"message": "Работает"}

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.post("/register")
async def register(user: UserCreate, session: AsyncSession = Depends(get_session)):
    existing_user = await get_user_by_username(session, user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    new_user = await create_user(session, user.username, user.password)
    return {"id": new_user.id, "username": new_user.username}

@app.post("/login")
async def login(user: UserLogin, session: AsyncSession = Depends(get_session)):
    existing_user = await get_user_by_username(session, user.username)
    if not existing_user or not verify_password(user.password, existing_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(data={"sub": existing_user.username})

    return {
        "message": "Login successful",
        "username": existing_user.username,
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username}

@app.get("/admin/users")
async def get_all_users(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("admin"))
):
    result = await session.execute(select(User))
    return result.scalars().all()

@app.post("/notes", response_model=NoteOut)
async def create_user_note(note: NoteCreate, session: AsyncSession = Depends(get_session), redis: redis.Redis = Depends(get_redis), user: User = Depends(get_current_user)):
    created_note = await create_note(session, note.text, user.id)
    await invalidate_notes_cache(redis, user.id)
    return created_note


@app.get("/notes", response_model=List[NoteOut])
async def read_notes(
    session: AsyncSession = Depends(get_session),
    redis: redis.Redis = Depends(get_redis),
    user: User = Depends(get_current_user),
    search: str = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1)
):
    cache_key = f"notes:{user.id}:{search}:{skip}:{limit}"
    cached_data = await redis.get(cache_key)
    if cached_data:
        print("[Cache HIT]")
        return json.loads(cached_data)
    
    print("[Cache MISS]")

    notes = await get_notes_with_filters(session, user.id, search, skip, limit)

    serialized_notes = json.dumps([note.model_dump() for note in [NoteOut.from_orm(n) for n in notes]], default=str)
    await redis.set(cache_key, serialized_notes, ex=600)

    return notes

@app.get("/notes/{note_id}", response_model=NoteOut)
async def read_note(note_id: int, session: AsyncSession = Depends(get_session), user = Depends(get_current_user)):
    note = await get_note(session, note_id, user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@app.put("/notes/{note_id}", response_model=NoteOut)
async def update_user_note(note_id: int, note_data: NoteUpdate, session: AsyncSession = Depends(get_session), redis: redis.Redis = Depends(get_redis), user: User = Depends(get_current_user)):
    note = await get_note(session, note_id, user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    updated_note = await update_note(session, note, note_data.dict(exclude_unset=True))
    await invalidate_notes_cache(redis, user.id)
    return updated_note

@app.delete("/notes/{note_id}")
async def delete_user_note(note_id: int, session: AsyncSession = Depends(get_session), redis: redis.Redis = Depends(get_redis), user: User = Depends(get_current_user)):
    note = await get_note(session, note_id, user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    await delete_note(session, note)
    await invalidate_notes_cache(redis, user.id)
    return {"ok": True}

@app.post("/trigger-task")
async def trigger_background_task(current_user: User = Depends(get_current_user)):
    send_mock_email.delay(current_user.username + "@gmail.com")
    return {"message": "Task started"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Client says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast("A client disconnected")