from api.client import ApiClient
from models.user import User, UserCreate, TokenResponse


class AuthApi:
    def __init__(self, client: ApiClient):
        self.client = client

    def register(self, login: str, password: str, is_admin: bool = False) -> User:
        data = UserCreate(login=login, password=password, is_admin=is_admin)
        result = self.client.post("/users/register", json=data.model_dump())
        return User(**result)

    def login(self, login: str, password: str) -> TokenResponse:
        result = self.client.post(
            "/users/login",
            data={"username": login, "password": password},
        )
        return TokenResponse(**result)

    def get_me(self) -> User:
        result = self.client.get("/users/me")
        return User(**result)
