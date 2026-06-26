import flet as ft
from api.client import ApiClient, ApiError
from api.movies import MoviesApi
from api.sessions import SessionsApi
from models.movie import Movie
from models.session import Session
from state.app_state import AppState
from widgets.movie_card import BillboardTile
from typing import Callable, Dict, Optional
from datetime import datetime, timedelta

TILE_GAP = 12

AGE_OPTIONS = [
    ft.dropdown.Option(key="0", text="0+"),
    ft.dropdown.Option(key="6", text="6+"),
    ft.dropdown.Option(key="12", text="12+"),
    ft.dropdown.Option(key="16", text="16+"),
    ft.dropdown.Option(key="18", text="18+"),
]


class BillboardView(ft.Column):
    def __init__(self, api_client: ApiClient, app_state: AppState, on_session_click: Callable[[int], None], on_movie_click: Callable[[int], None], halls_map: Optional[Dict[int, str]] = None):
        self._api_client = api_client
        self._app_state = app_state
        self._on_session_click = on_session_click
        self._on_movie_click = on_movie_click
        self._halls_map = halls_map or {}
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

        self._genre_filter = ft.Dropdown(
            label="Жанр",
            options=[],
            width=180,
        )
        self._genre_filter.on_change = self._on_filter_change

        self._age_filter = ft.Dropdown(
            label="Возраст",
            options=AGE_OPTIONS,
            width=120,
        )
        self._age_filter.on_change = self._on_filter_change

        self._tiles_container = ft.Container(
            padding=ft.padding.Padding(16, 0, 16, 0),
        )
        self._progress = ft.ProgressBar(visible=False, bar_height=2)
        self._empty_text = ft.Text("Сегодня актуальных сеансов нет", size=16, color=ft.Colors.ON_SURFACE_VARIANT, visible=False)

        super().__init__(
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            controls=[
                ft.Container(
                    padding=ft.padding.Padding(16, 16, 16, 0),
                    content=ft.Text("Афиша", size=28, weight=ft.FontWeight.BOLD),
                ),
                ft.Container(
                    padding=ft.padding.Padding(16, 0, 16, 0),
                    content=ft.Column(spacing=8, controls=[
                        self._search_field,
                        ft.Row(spacing=8, controls=[
                            self._genre_filter,
                            self._age_filter,
                        ]),
                    ]),
                ),
                self._progress,
                self._tiles_container,
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

    def _on_filter_change(self, e):
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
            self._populate_genre_options()
            self._render()
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")
        except Exception as ex:
            self._show_snackbar(f"Ошибка подключения: {ex}")
        finally:
            self._loading = False
            self._progress.visible = False
            self.update()

    def _populate_genre_options(self):
        genres = sorted({m.genre for m in self._movies})
        self._genre_filter.options = [ft.dropdown.Option(key=g, text=g) for g in genres]
        if self._genre_filter.page:
            self._genre_filter.update()

    def _apply_filters(self, movies: list[Movie]) -> list[Movie]:
        result = movies
        query = (self._search_field.value or "").strip().lower()
        if query:
            result = [m for m in result if query in m.title.lower() or query in m.genre.lower()]
        genre_val = self._genre_filter.value
        if genre_val:
            result = [m for m in result if m.genre == genre_val]
        age_val = self._age_filter.value
        if age_val is not None and age_val != "":
            result = [m for m in result if m.age_restriction == int(age_val)]
        return result

    def _render(self):
        now = datetime.now()
        today = now.date()

        movies_map = {m.id: m for m in self._movies}
        sessions_by_movie: dict[int, list[Session]] = {}
        for s in self._sessions:
            sessions_by_movie.setdefault(s.movie_id, []).append(s)

        movie_ids_active = set()
        for s in self._sessions:
            if s.datetime.date() == today:
                movie = movies_map.get(s.movie_id)
                if movie:
                    if s.datetime > now:
                        movie_ids_active.add(s.movie_id)

        movies_active = [m for m in self._movies if m.id in movie_ids_active]
        movies_active = self._apply_filters(movies_active)
        movies_active.sort(key=lambda m: m.age_restriction)

        self._empty_text.visible = not movies_active

        pw = int(self.page.width) if self.page else 1100
        nav_w = 0 if pw < 800 else 220
        content_w = pw - nav_w - 32

        if content_w < 500:
            cols = 2
        elif content_w < 800:
            cols = 3
        elif content_w < 1100:
            cols = 4
        else:
            cols = 5

        tile_w = max(140, (content_w - (cols - 1) * TILE_GAP) // cols)

        tiles = []
        for m in movies_active:
            tiles.append(BillboardTile(m, sessions_by_movie.get(m.id, []), self._on_session_click, self._on_movie_click, halls_map=self._halls_map, width=tile_w))

        self._tiles_container.content = ft.Row(
            wrap=True,
            spacing=TILE_GAP,
            run_spacing=TILE_GAP,
            controls=tiles,
        )
        self.update()

    def on_page_resize(self):
        self._render()

    def _show_snackbar(self, msg: str):
        if self.page:
            sb = ft.SnackBar(ft.Text(msg))
            self.page.overlay.append(sb)
            sb.open = True
            self.page.update()
