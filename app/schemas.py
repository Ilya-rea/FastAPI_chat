"""
Файл содержит Pydantic-схемы для валидации данных и сериализации.
- Определяет структуры данных для пользователей, чатов, групп и сообщений.
- Используется для валидации входных данных и формирования ответов API.
"""

from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True

class ChatCreate(BaseModel):
    name: str
    type: str  # "personal" или "group"

class ChatResponse(BaseModel):
    id: int
    name: str
    type: str

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    chat_id: int
    sender_id: int
    text: str
    is_read: Optional[bool] = False

class MessageResponse(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    text: str
    timestamp: datetime
    is_read: bool

class GroupCreate(BaseModel):
    name: str
    creator_id: int
    type: str
class GroupMemberCreate(BaseModel):
    user_id: int

class GroupResponse(BaseModel):
    id: int
    name: str
    creator_id: int
    members: List[int]

class ChatCreate(BaseModel):
    name: str
    type: str  # "personal" или "group"
    user1_id: Optional[int] = None
    user2_id: Optional[int] = None

class ChatResponse(BaseModel):
    id: int
    name: str
    type: str
    user1_id: Optional[int] = None
    user2_id: Optional[int] = None


    class Config:
        from_attributes = True


