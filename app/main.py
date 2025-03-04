"""
Точка входа в приложение, создает экземпляр FastAPI и настраивает маршруты.
- Инициализирует базу данных при старте приложения.
- Подключает REST-эндпоинты и WebSocket-эндпоинты.
- Добавлена JWT-аутентификация для защиты WebSocket-соединений.
"""

import asyncio
from fastapi import FastAPI, WebSocket, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from .api.endpoints import router as api_router
from .websocket import websocket_endpoint
from .database import init_db, AsyncSessionLocal
from .security import SECRET_KEY, ALGORITHM

app = FastAPI()
app.include_router(api_router)
# Схема для OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.on_event("startup")
async def startup_event():
    await asyncio.sleep(10)
    await init_db()


async def get_current_user_websocket(token: str, db: AsyncSession):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return email
    except JWTError:
        raise credentials_exception


@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Токен обязателен")
        return

    db = AsyncSessionLocal()
    try:
        email = await get_current_user_websocket(token, db)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Неверный токен")
        return
    finally:
        await db.close()

    chat_id = websocket.query_params.get("chat_id")
    group_id = websocket.query_params.get("group_id")

    if not chat_id and not group_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="chat_id или group_id обязателен")
        return

    await websocket.accept()

    if chat_id:
        await websocket_endpoint(websocket, int(chat_id), is_group=False, user_email=email)
    elif group_id:
        await websocket_endpoint(websocket, int(group_id), is_group=True, user_email=email)