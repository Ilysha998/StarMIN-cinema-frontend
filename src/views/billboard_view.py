import flet as ft
from api.client import ApiClient, ApiError
from api.movies import MoviesApi
from api.sessions import SessionsApi
from models.movie import Movie
from models.session import Session
from state.app_state import AppState
from widgets.movie_card import BillboardTile
from typing import Callable
from datetime import datetime, timedelta


TILE_W = 200
TILE_GAP = 12
TILE_PAD = 32


class BillboardView(ft.Column):
    def __init__(self, api_client: ApiClient, app_state: AppState, on_session_click: Callable[[int], None]):
        self._api_client = api_client
        self._app_state = app_state
        self._on_session_click = on_session_click
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
                    content=self._search_field,
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
        query = self._search_field.value.strip().lower()
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
        if query:
            movies_active = [
                m for m in movies_active
                if query in m.title.lower() or query in m.genre.lower()
            ]
        movies_active.sort(key=lambda m: m.age_restriction)

        tiles = []
        for m in movies_active:
            tiles.append(BillboardTile(m, sessions_by_movie.get(m.id, []), self._on_session_click))

        self._empty_text.visible = not tiles

        pw = int(self.page.width) if self.page else 1100
        avail = pw - TILE_PAD
        cols = max(1, int(avail // (TILE_W + TILE_GAP)))

        rows: list[ft.Row] = []
        for i in range(0, len(tiles), cols):
            row_tiles = tiles[i:i + cols]
            row = ft.Row(
                controls=row_tiles,
                spacing=TILE_GAP,
                alignment=ft.MainAxisAlignment.START if len(row_tiles) < cols else ft.MainAxisAlignment.START,
            )
            rows.append(row)

        self._tiles_container.content = ft.Column(spacing=TILE_GAP, controls=rows)
        self.update()

    def _show_snackbar(self, msg: str):
        if self.page:
            sb = ft.SnackBar(ft.Text(msg))
            self.page.overlay.append(sb)
            sb.open = True
            self.page.update()
