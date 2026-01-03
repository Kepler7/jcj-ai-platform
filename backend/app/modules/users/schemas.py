from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str  # 'school_admin' | 'teacher'
    school_id: Optional[UUID] = None

class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    school_id: Optional[UUID]
    is_active: bool

    class Config:
        from_attributes = True