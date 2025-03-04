"""
Файл содержит клиентскую часть для взаимодействия с WebSocket-сервером.
Позволяет пользователю отправлять сообщения в групповой чат через WebSocket.
- Запрашивает у пользователя ID отправителя, ID группы и текст сообщения.
- Формирует JSON-сообщение и отправляет его на сервер через WebSocket.
- Получает ответ от сервера и выводит его в консоль.
"""

import asyncio
import json
import websockets

async def send_message():
    sender_id = int(input("Введите ваш ID (отправитель): "))
    group_id = int(input("Введите ID группы: "))
    text = input("Введите текст сообщения: ")

    message = {
        "sender_id": sender_id,
        "text": text
    }


    async with websockets.connect(f"ws://localhost:8000/ws?group_id={group_id}") as websocket:
        await websocket.send(json.dumps(message))
        response = await websocket.recv()
        print(f"Ответ от сервера: {response}")

if __name__ == "__main__":
    asyncio.run(send_message())