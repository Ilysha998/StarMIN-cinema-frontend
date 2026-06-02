import flet as ft
from api.client import ApiClient, ApiError
from api.movies import MoviesApi
from api.sessions import SessionsApi
from models.movie import Movie
from models.session import Session
from state.app_state import AppState
from typing import Callable
from datetime import datetime, timedelta


AGE_COLORS = {
    0: ft.Colors.GREEN, 6: ft.Colors.BLUE, 12: ft.Colors.ORANGE,
    16: ft.Colors.DEEP_ORANGE, 18: ft.Colors.RED,
}


class FilmCard(ft.Container):
    def __init__(self, movie: Movie, has_sessions_today: bool, on_click: Callable[[int], None]):
        self._movie = movie
        self._on_click_fn = on_click
        age_c = AGE_COLORS.get(movie.age_restriction, ft.Colors.GREY)

        today_badge = ft.Container()
        if has_sessions_today:
            today_badge = ft.Container(
                padding=ft.padding.Padding(4, 8, 4, 8),
                border_radius=6,
                bgcolor=ft.Colors.GREEN,
                content=ft.Text("Сегодня", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_PRIMARY),
            )

        super().__init__(
            ink=True,
            on_click=lambda _: self._on_click_fn(movie.id),
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            padding=16,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(spacing=4, expand=True, controls=[
                        ft.Text(movie.title, size=16, weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Row(spacing=12, wrap=True, controls=[
                            ft.Row(spacing=4, controls=[
                                ft.Icon(ft.Icons.CATEGORY, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Text(movie.genre, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                            ]),
                            ft.Row(spacing=4, controls=[
                                ft.Icon(ft.Icons.TIMER_OUTLINED, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Text(f"{movie.duration} мин", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                            ]),
                        ]),
                    ]),
                    ft.Row(spacing=6, controls=[
                        today_badge if has_sessions_today else ft.Container(),
                        ft.Container(
                            padding=ft.padding.Padding(4, 8, 4, 8),
                            border_radius=6,
                            bgcolor=age_c,
                            content=ft.Text(f"{movie.age_restriction}+", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_PRIMARY),
                        ),
                    ]),
                ],
            ),
        )


class FilmsView(ft.Column):
    def __init__(self, api_client: ApiClient, app_state: AppState, on_movie_click: Callable[[int], None]):
        self._api_client = api_client
        self._app_state = app_state
        self._on_movie_click = on_movie_click
        self._movies_api = MoviesApi(api_client)
        self._sessions_api = SessionsApi(api_client)
        self._movies: list[Movie] = []
        self._sessions: list[Session] = []
        self._loading = False

        self._search_field = ft.TextField(
            hint_text="Поиск фильма...",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._on_search,
            expand=True,
        )

        self._cards_column = ft.Column(spacing=8)
        self._progress = ft.ProgressBar(visible=False, bar_height=2)
        self._empty_text = ft.Text("Фильмы не найдены", size=16, color=ft.Colors.ON_SURFACE_VARIANT, visible=False)

        super().__init__(
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            controls=[
                ft.Container(
                    padding=ft.padding.Padding(16, 16, 16, 0),
                    content=ft.Text("Фильмы", size=28, weight=ft.FontWeight.BOLD),
                ),
                ft.Container(
                    padding=ft.padding.Padding(16, 0, 16, 0),
                    content=self._search_field,
                ),
                self._progress,
                ft.Container(
                    padding=ft.padding.Padding(16, 0, 16, 0),
                    content=self._cards_column,
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

    def _on_search(self, e):
        self._render()

    def _load_data(self):
        if self._loading:
            return
        self._loading = True
        self._progress.visible = True
        self.update()

        try:
            self._movies = self._movies_api.get_all(skip=0, limit=100)
            self._sessions = self._sessions_api.get_all(skip=0, limit=100)
            self._render()
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")
        except Exception as ex:
            self._show_snackbar(f"Ошибка подключения: {ex}")
        finally:
            self._loading = False
            self._progress.visible = False
            self.update()

    def _render(self):
        self._cards_column.controls.clear()
        query = self._search_field.value.strip().lower()
        now = datetime.now()
        today = now.date()

        movies_map = {m.id: m for m in self._movies}
        movie_ids_today: set[int] = set()
        for s in self._sessions:
            if s.datetime.date() == today:
                movie_ids_today.add(s.movie_id)

        movies_with = [m for m in self._movies if m.id in movie_ids_today]
        movies_without = [m for m in self._movies if m.id not in movie_ids_today]

        if query:
            movies_with = [m for m in movies_with if query in m.title.lower() or query in m.genre.lower()]
            movies_without = [m for m in movies_without if query in m.title.lower() or query in m.genre.lower()]

        movies_with.sort(key=lambda m: m.age_restriction)
        movies_without.sort(key=lambda m: m.age_restriction)

        if not movies_with and not movies_without:
            self._empty_text.visible = True
        else:
            self._empty_text.visible = False
            if movies_with:
                self._cards_column.controls.append(
                    ft.Text("Сеансы сегодня", size=14, weight=ft.FontWeight.W_500, color=ft.Colors.PRIMARY)
                )
                for m in movies_with:
                    self._cards_column.controls.append(FilmCard(m, True, self._on_movie_click))
            if movies_without:
                self._cards_column.controls.append(ft.Divider())
                self._cards_column.controls.append(
                    ft.Text("Без сеансов сегодня", size=14, weight=ft.FontWeight.W_500, color=ft.Colors.ON_SURFACE_VARIANT)
                )
                for m in movies_without:
                    self._cards_column.controls.append(FilmCard(m, False, self._on_movie_click))

        self.update()

    def _show_snackbar(self, msg: str):
        if self.page:
            sb = ft.SnackBar(ft.Text(msg))
            self.page.overlay.append(sb)
            sb.open = True
            self.page.update()
