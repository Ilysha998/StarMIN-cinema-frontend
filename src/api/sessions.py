from typing import List, Optional
from api.client import ApiClient
from models.session import Session, SessionCreate, SessionUpdate, SessionWithTickets


class SessionsApi:
    def __init__(self, client: ApiClient):
        self.client = client

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Session]:
        result = self.client.get("/sessions", params={"skip": skip, "limit": limit})
        return [Session(**s) for s in result]

    def get_by_id(self, session_id: int) -> SessionWithTickets:
        result = self.client.get(f"/sessions/{session_id}")
        return SessionWithTickets(**result)

    def get_by_movie(self, movie_id: int, skip: int = 0, limit: int = 100) -> List[Session]:
        result = self.client.get(f"/sessions/movie/{movie_id}", params={"skip": skip, "limit": limit})
        return [Session(**s) for s in result]

    def get_by_hall(self, hall_id: int, skip: int = 0, limit: int = 100) -> List[Session]:
        result = self.client.get(f"/sessions/hall/{hall_id}", params={"skip": skip, "limit": limit})
        return [Session(**s) for s in result]

    def create(self, session: SessionCreate) -> Session:
        payload = session.model_dump(exclude_none=True)
        payload["datetime"] = session.datetime.isoformat()
        result = self.client.post("/sessions", json=payload)
        return Session(**result)

    def update(self, session_id: int, session: SessionUpdate) -> Session:
        payload = session.model_dump(exclude_none=True)
        if "datetime" in payload and payload["datetime"] is not None:
            payload["datetime"] = payload["datetime"].isoformat() if not isinstance(payload["datetime"], str) else payload["datetime"]
        result = self.client.put(f"/sessions/{session_id}", json=payload)
        return Session(**result)

    def delete(self, session_id: int) -> None:
        self.client.delete(f"/sessions/{session_id}")
