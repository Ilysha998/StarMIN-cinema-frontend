from pydantic import BaseModel, Field
from typing import Optional, List


class Ticket(BaseModel):
    id: int
    session_id: int
    user_id: int
    seat_number: int
    is_paid: bool


class TicketCreate(BaseModel):
    session_id: int = Field(..., gt=0)
    seat_number: int = Field(..., gt=0)


class TicketUpdate(BaseModel):
    is_paid: Optional[bool] = None


class AvailableSeats(BaseModel):
    session_id: int
    hall: str
    total_seats: int
    booked_count: int
    available_count: int
    available_seats: List[int]


class SalesStatistics(BaseModel):
    total_tickets_sold: int
    paid_tickets: int
    unpaid_tickets: int
    payment_percentage: float
    total_sessions: int
    average_tickets_per_session: float
