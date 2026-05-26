import flet as ft
from api.client import ApiClient, ApiError
from api.movies import MoviesApi
from api.sessions import SessionsApi
from models.movie import Movie
from models.session import Session
from state.app_state import AppState
from widgets.session_card import SessionCard
from typing import Callable, Optional


AGE_LABELS = {0: "0+", 6: "6+", 12: "12+", 16: "16+", 18: "18+"}


class MovieDetailView(ft.Column):
    def __init__(self, api_client: ApiClient, app_state: AppState, movie_id: int, on_session_click: Callable[[int], None], on_back: Callable):
        self._api_client = api_client
        self._app_state = app_state
        self._movie_id = movie_id
        self._on_session_click = on_session_click
        self._on_back = on_back
        self._movies_api = MoviesApi(api_client)
        self._sessions_api = SessionsApi(api_client)
        self._movie: Optional[Movie] = None
        self._sessions: list[Session] = []

        self._back_btn = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            on_click=lambda _: self._on_back(),
        )
        self._progress = ft.ProgressBar(visible=False, bar_height=2)
        self._info_section = ft.Container()
        self._sessions_column = ft.Column(spacing=8)

        super().__init__(
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            controls=[
                ft.Container(
                    padding=16,
                    content=ft.Row(controls=[self._back_btn, ft.Text("Детали фильма", size=24, weight=ft.FontWeight.BOLD)]),
                ),
                self._progress,
                ft.Container(padding=ft.padding.Padding(16, 0, 16, 0), content=self._info_section),
                ft.Container(
                    padding=16,
                    content=ft.Column([
                        ft.Text("Сеансы", size=18, weight=ft.FontWeight.BOLD),
                        self._sessions_column,
                    ]),
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
            self._movie = self._movies_api.get_by_id(self._movie_id)
            self._sessions = self._sessions_api.get_by_movie(self._movie_id)
            self._render()
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")
        except Exception as ex:
            self._show_snackbar(f"Ошибка подключения: {ex}")
        finally:
            self._progress.visible = False
            self.update()

    def _render(self):
        m = self._movie
        if not m:
            return

        age_label = AGE_LABELS.get(m.age_restriction, f"{m.age_restriction}+")
        age_color = {
            0: ft.Colors.GREEN, 6: ft.Colors.BLUE, 12: ft.Colors.ORANGE,
            16: ft.Colors.DEEP_ORANGE, 18: ft.Colors.RED,
        }.get(m.age_restriction, ft.Colors.GREY)

        self._info_section.content = ft.Column(
            spacing=12,
            controls=[
                ft.Container(
                    height=200,
                    bgcolor=ft.Colors.SURFACE_CONTAINER,
                    border_radius=12,
                    alignment=ft.alignment.Alignment(0, 0),
                    content=ft.Icon(ft.Icons.MOVIE_OUTLINED, size=80, color=ft.Colors.ON_SURFACE_VARIANT),
                ),
                ft.Text(m.title, size=28, weight=ft.FontWeight.BOLD),
                ft.Row(
                    spacing=16,
                    controls=[
                        ft.Container(
                            padding=ft.padding.Padding(6, 12, 6, 12),
                            border_radius=8,
                            bgcolor=age_color,
                            content=ft.Text(age_label, size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_PRIMARY),
                        ),
                        ft.Row(spacing=4, controls=[
                            ft.Icon(ft.Icons.CATEGORY, size=18, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(m.genre, size=15, color=ft.Colors.ON_SURFACE_VARIANT),
                        ]),
                        ft.Row(spacing=4, controls=[
                            ft.Icon(ft.Icons.TIMER_OUTLINED, size=18, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(f"{m.duration} мин", size=15, color=ft.Colors.ON_SURFACE_VARIANT),
                        ]),
                    ],
                ),
            ],
        )

        self._sessions_column.controls.clear()
        if not self._sessions:
            self._sessions_column.controls.append(
                ft.Text("Нет сеансов для этого фильма", color=ft.Colors.ON_SURFACE_VARIANT)
            )
        else:
            for s in self._sessions:
                card = SessionCard(s, movie_title=m.title, on_click=self._on_session_click)
                self._sessions_column.controls.append(card)

    def _show_snackbar(self, msg: str):
        if self.page:
            sb = ft.SnackBar(ft.Text(msg))
            self.page.overlay.append(sb)
            sb.open = True
            self.page.update()
