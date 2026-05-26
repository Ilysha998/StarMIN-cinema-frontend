import flet as ft
from api.client import ApiClient, ApiError
from api.sessions import SessionsApi
from api.movies import MoviesApi
from models.session import Session
from models.movie import Movie
from state.app_state import AppState
from widgets.session_card import SessionCard
from typing import Callable, Optional


HALL_FILTERS = [("all", "Все"), ("1", "Зал 1"), ("2", "Зал 2"), ("vip", "VIP")]


class SessionsView(ft.Column):
    def __init__(self, api_client: ApiClient, app_state: AppState, on_session_click: Callable[[int], None]):
        self._api_client = api_client
        self._app_state = app_state
        self._on_session_click = on_session_click
        self._sessions_api = SessionsApi(api_client)
        self._movies_api = MoviesApi(api_client)
        self._sessions: list[Session] = []
        self._movies_map: dict[int, Movie] = {}
        self._current_hall = "all"

        self._hall_chips = ft.Row(spacing=8)
        for hall_key, hall_label in HALL_FILTERS:
            chip = ft.Chip(
                label=ft.Text(hall_label),
                selected=hall_key == "all",
                on_select=lambda e, k=hall_key: self._filter_by_hall(k),
            )
            self._hall_chips.controls.append(chip)

        self._progress = ft.ProgressBar(visible=False, bar_height=2)
        self._sessions_column = ft.Column(spacing=8)
        self._empty_text = ft.Text("Сеансы не найдены", size=16, color=ft.Colors.ON_SURFACE_VARIANT, visible=False)

        super().__init__(
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            controls=[
                ft.Container(
                    padding=ft.padding.Padding(16, 16, 16, 0),
                    content=ft.Text("Сеансы", size=24, weight=ft.FontWeight.BOLD),
                ),
                ft.Container(padding=ft.padding.Padding(16, 0, 16, 0), content=self._hall_chips),
                self._progress,
                ft.Container(
                    padding=ft.padding.Padding(16, 0, 16, 0),
                    content=self._sessions_column,
                ),
                ft.Container(
                    padding=16,
                    alignment=ft.alignment.Alignment(0, 0),
                    content=self._empty_text,
                ),
            ],
            expand=True,
        )

    def did_mount(self):
        self._load_data()

    def _load_data(self):
        self._progress.visible = True
        self.update()

        try:
            movies = self._movies_api.get_all(skip=0, limit=100)
            self._movies_map = {m.id: m for m in movies}
            self._load_sessions()
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")
        except Exception as ex:
            self._show_snackbar(f"Ошибка подключения: {ex}")
        finally:
            self._progress.visible = False
            self.update()

    def _load_sessions(self):
        try:
            if self._current_hall == "all":
                self._sessions = self._sessions_api.get_all(skip=0, limit=100)
            else:
                self._sessions = self._sessions_api.get_by_hall(self._current_hall, skip=0, limit=100)
            self._render()
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")

    def _filter_by_hall(self, hall: str):
        self._current_hall = hall
        for i, (hk, _) in enumerate(HALL_FILTERS):
            self._hall_chips.controls[i].selected = hk == hall
        self.update()
        self._load_sessions()

    def _render(self):
        self._sessions_column.controls.clear()
        if not self._sessions:
            self._empty_text.visible = True
        else:
            self._empty_text.visible = False
            for s in self._sessions:
                movie_title = self._movies_map.get(s.movie_id, None)
                movie_title = movie_title.title if movie_title else None
                card = SessionCard(s, movie_title=movie_title, on_click=self._on_session_click)
                self._sessions_column.controls.append(card)
        self.update()

    def _show_snackbar(self, msg: str):
        if self.page:
            sb = ft.SnackBar(ft.Text(msg))
            self.page.overlay.append(sb)
            sb.open = True
            self.page.update()
