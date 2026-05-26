from typing import Optional, List
from models.user import User
from models.movie import Movie
from models.session import Session
from models.ticket import Ticket


class AppState:
    def __init__(self):
        self.token: Optional[str] = None
        self.current_user: Optional[User] = None
        self.movies: List[Movie] = []
        self.sessions: List[Session] = []
        self.tickets: List[Ticket] = []

    @property
    def is_logged_in(self) -> bool:
        return self.token is not None

    @property
    def is_admin(self) -> bool:
        return self.current_user is not None and self.current_user.is_admin

    def set_auth(self, token: str, user: User):
        self.token = token
        self.current_user = user

    def clear_auth(self):
        self.token = None
        self.current_user = None
        self.tickets = []
