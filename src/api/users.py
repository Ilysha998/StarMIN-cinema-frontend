from typing import List, Optional
from api.client import ApiClient
from models.user import User, UserCreate, UserUpdate


class UsersApi:
    def __init__(self, client: ApiClient):
        self.client = client

    def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        result = self.client.get("/users", params={"skip": skip, "limit": limit})
        return [User(**u) for u in result]

    def get_by_id(self, user_id: int) -> User:
        result = self.client.get(f"/users/{user_id}")
        return User(**result)

    def update(self, user_id: int, user: UserUpdate) -> User:
        result = self.client.put(f"/users/{user_id}", json=user.model_dump(exclude_none=True))
        return User(**result)

    def delete(self, user_id: int) -> None:
        self.client.delete(f"/users/{user_id}")

    def change_password(self, user_id: int, old_password: str, new_password: str) -> dict:
        result = self.client.post(
            f"/users/change-password/{user_id}",
            json={"old_password": old_password, "new_password": new_password},
        )
        return result
