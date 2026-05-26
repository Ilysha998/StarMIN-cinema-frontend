from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class HallEnum(str, Enum):
    hall_1 = "1"
    hall_2 = "2"
    hall_vip = "vip"


class Session(BaseModel):
    id: int
    movie_id: int
    datetime: datetime
    hall: str
    price: float


class SessionWithTickets(Session):
    tickets: List[dict] = []


class SessionCreate(BaseModel):
    movie_id: int = Field(..., gt=0)
    datetime: datetime
    hall: HallEnum
    price: float = Field(..., gt=0)


class SessionUpdate(BaseModel):
    movie_id: Optional[int] = Field(None, gt=0)
    datetime: Optional[datetime] = None
    hall: Optional[HallEnum] = None
    price: Optional[float] = Field(None, gt=0)
