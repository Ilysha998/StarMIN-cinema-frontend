from typing import List
from api.client import ApiClient
from models.hall import Hall


class HallsApi:
    def __init__(self, client: ApiClient):
        self.client = client

    def get_all(self) -> List[Hall]:
        result = self.client.get("/halls")
        return [Hall(**h) for h in result]

    def get_by_id(self, hall_id: int) -> Hall:
        result = self.client.get(f"/halls/{hall_id}")
        return Hall(**result)
