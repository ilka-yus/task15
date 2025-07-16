from sqlmodel import select
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user_by_username(session: AsyncSession, username: str) -> User:
    statement = select(User).where(User.username == username)
    result = await session.execute(statement)
    return result.scalar_one_or_none()