# FastAPI Chat 

Этот проект представляет собой мессенджер, реализованный на FastAPI с использованием PostgreSQL, WebSocket и Docker. Он поддерживает личные и групповые чаты, аутентификацию и хранение истории сообщений.

## Оглавление

- [Запуск проекта через Docker](#запуск-проекта-через-docker)
- [Примеры API-запросов](#примеры-api-запросов)
  - [Регистрация пользователя](#1-регистрация-пользователя)
  - [Вход в систему и получение токена](#2-вход-в-систему-и-получение-токена)
  - [Создание чата](#3-создание-чата)
  - [Создание группы](#4-создание-группы)
  - [Получение истории сообщений](#5-получение-истории-сообщений)
- [Создание тестовых данных](#создание-тестовых-данных)
- [Лицензия](#лицензия)

## Запуск проекта через Docker

1. Убедитесь, что у вас установлены Docker и Docker Compose.
2. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/your-repo/fastapi-chat.git
   cd fastapi-chat
   ```
3. Запустите проект с помощью Docker Compose:
   ```bash
   docker-compose up --build
   ```
   Это запустит два контейнера:
   - `app` — FastAPI-приложение на порту 8000.
   - `db` — PostgreSQL база данных на порту 5432.

После запуска приложение будет доступно по адресу:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

## Примеры API-запросов

### 1. Регистрация пользователя
```bash
curl -X POST "http://localhost:8000/register/" \
-H "Content-Type: application/json" \
-d '{
  "name": "testuser",
  "email": "test@example.com",
  "password": "testpassword"
}'
```

### 2. Вход в систему и получение токена
```bash
curl -X POST "http://localhost:8000/token/" \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "username=test@example.com&password=testpassword"
```

### 3. Создание чата
```bash
curl -X POST "http://localhost:8000/chats/" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer <access_token>" \
-d '{
  "name": "Test Chat",
  "type": "personal",
  "user1_id": 1,
  "user2_id": 2
}'
```

### 4. Создание группы
```bash
curl -X POST "http://localhost:8000/groups/" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer <access_token>" \
-d '{
  "name": "Test Group",
  "creator_id": 1
}'
```

### 5. Получение истории сообщений
```bash
curl -X GET "http://localhost:8000/history/1" \
-H "Authorization: Bearer <access_token>"
```


