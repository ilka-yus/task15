from sqlalchemy.future import select
from app.models import User, Note
from app.security import get_password_hash
from sqlalchemy.ext.asyncio import AsyncSession

async def create_user(session: AsyncSession, username: str, password: str) -> User:
    hashed_password = get_password_hash(password)
    user = User(username=username, hashed_password=hashed_password)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

async def create_note(session: AsyncSession, text: str, user_id: int) -> Note:
    note = Note(text=text, owner_id=user_id)
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return note

async def get_notes_by_user(session: AsyncSession, user_id: int) -> Note:
    result = await session.execute(select(Note).where(Note.owner_id == user_id))
    return result.scalars().all()

async def get_note(session: AsyncSession, note_id: int, user_id: int) -> Note:
    result = await session.execute(select(Note).where(Note.id == note_id, Note.owner_id == user_id))
    return result.scalar_one_or_none()

async def update_note(session: AsyncSession, note, update_data: dict) -> Note:
    for key, value in update_data.items():
        setattr(note, key, value)
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return note

async def delete_note(session: AsyncSession, note) -> Note:
    await session.delete(note)
    await session.commit()

async def get_notes_with_filters(session: AsyncSession, user_id: int, search: str = None, skip: int = 0, limit: int = 100) -> Note:
    statement = select(Note).where(Note.owner_id == user_id)

    if search:
        statement = statement.where(Note.text.ilike(f"%{search}%"))

    statement = statement.offset(skip).limit(limit)

    result = await session.execute(statement)
    return result.scalars().all()