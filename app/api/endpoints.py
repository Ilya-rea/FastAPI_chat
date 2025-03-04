"""
Файл содержит REST-эндпоинты для работы с API.
- Реализует CRUD-операции для пользователей, чатов, групп и сообщений.
- Предоставляет эндпоинты для:
  - Создания пользователей.
  - Получения истории сообщений.
  - Создания чатов и групп.
  - Добавления участников в группы.
  - Помечения сообщений как прочитанных.
- Добавлена JWT-аутентификация для защиты эндпоинтов.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from ..database import AsyncSessionLocal
from .. import crud, schemas, models, security

router = APIRouter()

async def get_db():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()

async def get_current_user(token: str = Depends(security.oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = security.jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except security.JWTError:
        raise credentials_exception
    user = await crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

# Эндпоинт для регистрации пользователя
@router.post("/register/", response_model=schemas.UserResponse)
async def register_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = security.get_password_hash(user.password)
    db_user = models.User(name=user.name, email=user.email, password=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/token/", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me/", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.get("/history/{chat_id}", response_model=list[schemas.MessageResponse])
async def read_history(
    chat_id: int,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    messages = await crud.get_messages(db, chat_id=chat_id, limit=limit, offset=offset)
    return messages


@router.post("/chats/", response_model=schemas.ChatResponse)
async def create_chat(
    chat: schemas.ChatCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if chat.type not in ["personal", "group"]:
        raise HTTPException(status_code=400, detail="Недопустимый тип чата. Допустимые значения: 'personal', 'group'")

    if chat.type == "personal" and (not chat.user1_id or not chat.user2_id):
        raise HTTPException(status_code=400, detail="Для личного чата необходимо указать user1_id и user2_id")

    db_chat = models.Chat(
        name=chat.name,
        type=chat.type,
        user1_id=chat.user1_id if chat.type == "personal" else None,
        user2_id=chat.user2_id if chat.type == "personal" else None
    )
    db.add(db_chat)
    await db.commit()
    await db.refresh(db_chat)
    return db_chat

# Эндпоинт для создания группы (защищенный)
@router.post("/groups/", response_model=schemas.GroupResponse)
async def create_group(
    group: schemas.GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_group = models.Group(name=group.name, creator_id=current_user.id)
    db.add(db_group)
    await db.commit()
    await db.refresh(db_group)

    db_member = models.GroupMember(group_id=db_group.id, user_id=current_user.id)
    db.add(db_member)
    await db.commit()

    return {
        "id": db_group.id,
        "name": db_group.name,
        "creator_id": db_group.creator_id,
        "members": [current_user.id]
    }

@router.post("/groups/{group_id}/members/", response_model=schemas.GroupResponse)
async def add_member(
    group_id: int,
    member: schemas.GroupMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_group = await crud.add_member_to_group(db, group_id, member.user_id)
    if not db_group:
        raise HTTPException(status_code=404, detail="Group not found")
    return db_group


@router.get("/groups/{group_id}", response_model=schemas.GroupResponse)
async def read_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_group = await crud.get_group(db, group_id)
    if not db_group:
        raise HTTPException(status_code=404, detail="Group not found")
    return db_group


@router.post("/messages/{message_id}/mark_as_read/", response_model=schemas.MessageResponse)
async def mark_message_as_read(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_message = await crud.mark_message_as_read(db, message_id)
    if not db_message:
        raise HTTPException(status_code=404, detail="Message not found")
    return db_message