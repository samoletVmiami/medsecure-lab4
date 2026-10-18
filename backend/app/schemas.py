from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

# --- Пользователи ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    role: Optional[str] = "doctor"

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    username: str
    password: str
    
class UserOut(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# --- Аутентификация ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

# --- Зоны безопасности клиники ---
class ZoneBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    clearance_level: int = Field(..., ge=1, le=4)
    status: str = Field(default="В норме")
    description: Optional[str] = None

class ZoneCreate(ZoneBase):
    pass

class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    clearance_level: Optional[int] = Field(None, ge=1, le=4)
    status: Optional[str] = None
    description: Optional[str] = None

class ZoneOut(ZoneBase):
    id: int
    created_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Пагинация для списка зон ---
class PaginatedZones(BaseModel):
    total: int
    page: int
    limit: int
    items: List[ZoneOut]