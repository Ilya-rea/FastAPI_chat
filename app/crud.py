"""
Файл содержит функции для взаимодействия с базой данных.
Использует SQLAlchemy для выполнения асинхронных запросов к PostgreSQL.

Основные функции:
- create_user(): Создает нового пользователя.
- get_user_by_email(): Получает пользователя по email.
- create_chat(): Создает новый чат.
- get_chat_by_id(): Получает чат по ID.
- create_message(): Создает новое сообщение.
- get_messages(): Получает историю сообщений для чата.
- mark_message_as_read(): Помечает сообщение как прочитанное.
- create_group(): Создает новую группу.
- add_member_to_group(): Добавляет участника в группу.
- get_group(): Получает информацию о группе.
- create_personal_chat(): Создает личный чат между двумя пользователями.
"""

import hashlib
from http.client import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from . import models, schemas


async def create_user(db: AsyncSession, user: schemas.UserCreate):
    db_user = models.User(name=user.name, email=user.email, password=user.password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.User).filter(models.User.email == email))
    return result.scalars().first()


async def create_chat(db: AsyncSession, chat: schemas.ChatCreate):
    db_chat = models.Chat(name=chat.name, type=chat.type)
    db.add(db_chat)
    await db.commit()
    await db.refresh(db_chat)
    return db_chat


async def get_chat_by_id(db: AsyncSession, chat_id: int):
    result = await db.execute(select(models.Chat).filter(models.Chat.id == chat_id))
    return result.scalars().first()


async def create_message(db: AsyncSession, message: schemas.MessageCreate):
    message_hash = hashlib.sha256(f"{message.chat_id}_{message.sender_id}_{message.text}".encode()).hexdigest()
    existing_message = await db.execute(
        select(models.Message).filter(models.Message.message_hash == message_hash)
    )
    if existing_message.scalars().first():
        raise HTTPException(status_code=400, detail="Сообщение уже отправлено")

    db_message = models.Message(
        chat_id=message.chat_id,
        sender_id=message.sender_id,
        text=message.text,
        is_read=message.is_read,
        message_hash=message_hash
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    return db_message


async def get_messages(db: AsyncSession, chat_id: int, limit: int = 100, offset: int = 0):
    result = await db.execute(
        select(models.Message)
        .filter(models.Message.chat_id == chat_id)
        .order_by(models.Message.timestamp.asc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def mark_message_as_read(db: AsyncSession, message_id: int):
    result = await db.execute(select(models.Message).filter(models.Message.id == message_id))
    db_message = result.scalars().first()
    if db_message:
        db_message.is_read = True
        await db.commit()
        await db.refresh(db_message)
    return db_message


async def create_group(db: AsyncSession, group: schemas.GroupCreate):
    db_user = await db.get(models.User, group.creator_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_chat = models.Chat(name=group.name, type="group")
    db.add(db_chat)
    await db.commit()
    await db.refresh(db_chat)

    db_group = models.Group(name=group.name, creator_id=group.creator_id, chat_id=db_chat.id)
    db.add(db_group)
    await db.commit()
    await db.refresh(db_group)

    db_member = models.GroupMember(group_id=db_group.id, user_id=group.creator_id)
    db.add(db_member)
    await db.commit()

    members_result = await db.execute(
        select(models.GroupMember.user_id).filter(models.GroupMember.group_id == db_group.id)
    )
    members = members_result.scalars().all()

    return {
        "id": db_group.id,
        "name": db_group.name,
        "creator_id": db_group.creator_id,
        "type": db_chat.type,
        "members": members
    }


async def add_member_to_group(db: AsyncSession, group_id: int, user_id: int):
    db_group = await db.get(models.Group, group_id)
    if not db_group:
        raise HTTPException(status_code=404, detail="Group not found")

    db_user = await db.get(models.User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_member = await db.execute(
        select(models.GroupMember)
        .filter(models.GroupMember.group_id == group_id)
        .filter(models.GroupMember.user_id == user_id)
    )
    if existing_member.scalars().first():
        raise HTTPException(status_code=400, detail="User already in group")

    db_member = models.GroupMember(group_id=group_id, user_id=user_id)
    db.add(db_member)
    await db.commit()

    members_result = await db.execute(
        select(models.GroupMember.user_id).filter(models.GroupMember.group_id == group_id)
    )
    members = members_result.scalars().all()

    return {
        "id": db_group.id,
        "name": db_group.name,
        "creator_id": db_group.creator_id,
        "members": members
    }


async def get_group(db: AsyncSession, group_id: int):
    result = await db.execute(
        select(models.Group)
        .options(joinedload(models.Group.members))
        .filter(models.Group.id == group_id)
    )
    db_group = result.scalars().first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Group not found")

    members_result = await db.execute(
        select(models.GroupMember.user_id).filter(models.GroupMember.group_id == group_id)
    )
    members = members_result.scalars().all()

    return {
        "id": db_group.id,
        "name": db_group.name,
        "creator_id": db_group.creator_id,
        "members": members
    }

async def create_personal_chat(db: AsyncSession, user1_id: int, user2_id: int):
    existing_chat = await db.execute(
        select(models.Chat)
        .filter(
            (models.Chat.user1_id == user1_id) & (models.Chat.user2_id == user2_id) |
            (models.Chat.user1_id == user2_id) & (models.Chat.user2_id == user1_id)
        )
        .filter(models.Chat.type == "personal")
    )
    if existing_chat.scalars().first():
        raise HTTPException(status_code=400, detail="Личный чат уже существует")

    db_chat = models.Chat(
        type="personal",
        user1_id=user1_id,
        user2_id=user2_id
    )
    db.add(db_chat)
    await db.commit()
    await db.refresh(db_chat)
    return db_chat