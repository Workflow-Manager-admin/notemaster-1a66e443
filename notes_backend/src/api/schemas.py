"""Pydantic schemas for the notes app REST API"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# -------------------
# User schemas
# -------------------

# PUBLIC_INTERFACE
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, description="Unique username")
    email: EmailStr


# PUBLIC_INTERFACE
class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128, description="Password (plaintext, for registration)")


# PUBLIC_INTERFACE
class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


# -------------------
# Token schemas
# -------------------

# PUBLIC_INTERFACE
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# PUBLIC_INTERFACE
class TokenData(BaseModel):
    username: Optional[str] = None


# -------------------
# Note schemas
# -------------------

# PUBLIC_INTERFACE
class NoteBase(BaseModel):
    title: str = Field(..., max_length=200)
    content: Optional[str] = None


# PUBLIC_INTERFACE
class NoteCreate(NoteBase):
    pass


# PUBLIC_INTERFACE
class NoteUpdate(NoteBase):
    title: Optional[str] = None
    content: Optional[str] = None


# PUBLIC_INTERFACE
class NoteOut(NoteBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# -------------------
# Misc
# -------------------

# PUBLIC_INTERFACE
class Message(BaseModel):
    detail: str

