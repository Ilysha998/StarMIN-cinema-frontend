from typing import List, Optional
from api.client import ApiClient
from models.ticket import Ticket, TicketCreate, TicketUpdate, AvailableSeats, SalesStatistics


class TicketsApi:
    def __init__(self, client: ApiClient):
        self.client = client

    def get_my(self) -> List[dict]:
        return self.client.get("/tickets/my")

    def get_my_enriched(self) -> List[dict]:
        return self.client.get("/users/me/tickets")

    def get_all(self, session_id: Optional[int] = None, is_paid: Optional[bool] = None, skip: int = 0, limit: int = 100) -> List[Ticket]:
        params = {"skip": skip, "limit": limit}
        if session_id is not None:
            params["session_id"] = session_id
        if is_paid is not None:
            params["is_paid"] = is_paid
        result = self.client.get("/tickets", params=params)
        return [Ticket(**t) for t in result]

    def get_by_session(self, session_id: int) -> List[Ticket]:
        result = self.client.get(f"/tickets/session/{session_id}")
        return [Ticket(**t) for t in result]

    def get_available_seats(self, session_id: int) -> AvailableSeats:
        result = self.client.get(f"/tickets/session/{session_id}/available-seats")
        return AvailableSeats(**result)

    def get_sales_statistics(self) -> SalesStatistics:
        result = self.client.get("/tickets/statistics/sales")
        return SalesStatistics(**result)

    def buy(self, session_id: int, seat_number: int, phone: Optional[str] = None, email: Optional[str] = None) -> Ticket:
        data = TicketCreate(session_id=session_id, seat_number=seat_number, phone=phone, email=email)
        result = self.client.post("/tickets", json=data.model_dump(exclude_none=True))
        return Ticket(**result)

    def update(self, ticket_id: int, ticket: TicketUpdate) -> Ticket:
        result = self.client.put(f"/tickets/{ticket_id}", json=ticket.model_dump(exclude_none=True))
        return Ticket(**result)

    def cancel(self, ticket_id: int) -> None:
        self.client.delete(f"/tickets/{ticket_id}")
