from pydantic import BaseModel, Field
from typing import List, Optional


class Hall(BaseModel):
    id: int
    name: str
    layout: List[List[str]]
    break_minutes: int
    base_price: float
    seat_count: int
