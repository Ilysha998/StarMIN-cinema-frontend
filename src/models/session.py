from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class Session(BaseModel):
    id: int
    movie_id: int
    datetime: datetime
    hall_id: int
    price: float


class SessionWithTickets(Session):
    tickets: List[dict] = []


class SessionCreate(BaseModel):
    movie_id: int = Field(..., gt=0)
    datetime: datetime
    hall_id: int = Field(..., gt=0)
    price: float = Field(..., gt=0)


class SessionUpdate(BaseModel):
    movie_id: Optional[int] = Field(None, gt=0)
    datetime: Optional[datetime] = None
    hall_id: Optional[int] = Field(None, gt=0)
    price: Optional[float] = Field(None, gt=0)
