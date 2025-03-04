"""
Файл содержит логику работы с WebSocket для реализации real-time обмена сообщениями.
- Управляет подключениями пользователей через класс ConnectionManager.
- Обрабатывает отправку и получение сообщений.
- Реализует broadcast-рассылку сообщений всем участникам чата или группы.
- Обрабатывает статус "прочитано" для сообщений.
"""

import json
from http.client import HTTPException
from venv import logger
from fastapi import WebSocket
from . import crud, models, schemas
from .crud import create_message, mark_message_as_read
from .database import AsyncSessionLocal
from .schemas import MessageCreate

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, chat_id: int):
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = []
        self.active_connections[chat_id].append(websocket)

    def disconnect(self, websocket: WebSocket, chat_id: int):
        if chat_id in self.active_connections:
            self.active_connections[chat_id].remove(websocket)
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, chat_id: int, message: str):
        if chat_id in self.active_connections:
            for connection in self.active_connections[chat_id]:
                await connection.send_text(message)

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket, chat_or_group_id: int, is_group: bool):
    await manager.connect(websocket, chat_or_group_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                sender_id = message_data.get("sender_id")
                text = message_data.get("text")
                action = message_data.get("action")

                if not sender_id or not text:
                    await websocket.send_text(json.dumps({"error": "Неверный формат сообщения"}))
                    continue

                db = AsyncSessionLocal()

                try:
                    if action == "send_message":
                        if is_group:
                            chat = await db.get(models.Group, chat_or_group_id)
                        else:
                            chat = await db.get(models.Chat, chat_or_group_id)

                        if not chat:
                            await websocket.send_text(json.dumps({"error": "Чат или группа не найдена"}))
                            continue

                        message_create = schemas.MessageCreate(
                            chat_id=chat.id if not is_group else chat.chat_id,
                            sender_id=sender_id,
                            text=text,
                            is_read=False
                        )

                        message = await crud.create_message(db, message_create)
                        await db.close()

                        await manager.broadcast(chat_or_group_id, json.dumps({
                            "id": message.id,
                            "chat_id": message.chat_id,
                            "sender_id": message.sender_id,
                            "text": message.text,
                            "timestamp": message.timestamp.isoformat(),
                            "is_read": message.is_read,
                            "action": "new_message"
                        }))

                    elif action == "mark_as_read":
                        message_id = message_data.get("message_id")
                        if not message_id:
                            await websocket.send_text(json.dumps({"error": "Не указан ID сообщения"}))
                            continue

                        message = await crud.mark_message_as_read(db, message_id)
                        if not message:
                            await websocket.send_text(json.dumps({"error": "Сообщение не найдено"}))
                            continue

                        await manager.broadcast(chat_or_group_id, json.dumps({
                            "id": message.id,
                            "chat_id": message.chat_id,
                            "sender_id": message.sender_id,
                            "text": message.text,
                            "timestamp": message.timestamp.isoformat(),
                            "is_read": message.is_read,
                            "action": "message_read"
                        }))

                except HTTPException as e:
                    await websocket.send_text(json.dumps({"error": e.detail}))
                except Exception as e:
                    logger.error(f"Ошибка при обработке сообщения: {e}")
                    await websocket.send_text(json.dumps({"error": "Внутренняя ошибка сервера"}))
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Неверный формат JSON"}))
            except Exception as e:
                logger.error(f"Ошибка при обработке сообщения: {e}")
                await websocket.send_text(json.dumps({"error": "Внутренняя ошибка сервера"}))
    except Exception as e:
        manager.disconnect(websocket, chat_or_group_id)
        logger.error(f"WebSocket error: {e}")