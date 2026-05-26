from pydantic import BaseModel, Field
from typing import Optional, List


class User(BaseModel):
    id: int
    login: str
    is_admin: bool


class UserCreate(BaseModel):
    login: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=255)
    is_admin: bool = False


class UserUpdate(BaseModel):
    password: Optional[str] = Field(None, min_length=6, max_length=255)
    is_admin: Optional[bool] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    login: str
    is_admin: bool


class LoginRequest(BaseModel):
    login: str
    password: str


class UserTicketInfo(BaseModel):
    id: int
    seat_number: int
    is_paid: bool
    session_id: int
    session_datetime: Optional[str] = None
    hall: Optional[str] = None
    price: Optional[float] = None
    movie_title: Optional[str] = None
