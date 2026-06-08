from pydantic import BaseModel, Field
from typing import Optional, List


class Ticket(BaseModel):
    id: int
    session_id: int
    user_id: Optional[int] = None
    seat_row: int
    seat_col: int
    seat_type: str
    price: float
    is_paid: bool
    qr_token: str
    phone: Optional[str] = None
    email: Optional[str] = None


class SeatItem(BaseModel):
    row: int = Field(..., ge=0)
    col: int = Field(..., ge=0)


class BuyRequest(BaseModel):
    session_id: int = Field(..., gt=0)
    seats: List[SeatItem] = Field(..., min_length=1)
    phone: Optional[str] = None
    email: Optional[str] = None


class TicketUpdate(BaseModel):
    is_paid: Optional[bool] = None


class SeatMapCell(BaseModel):
    type: str
    status: str


class SeatMap(BaseModel):
    session_id: int
    hall_id: int
    hall_name: str
    seat_map: List[List[SeatMapCell]]
    available_count: int
    booked_count: int
    total_seats: int


class SalesStatistics(BaseModel):
    total_tickets_sold: int
    paid_tickets: int
    unpaid_tickets: int
    payment_percentage: float
    total_sessions: int
    average_tickets_per_session: float
