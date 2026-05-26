import flet as ft
from api.client import ApiClient, ApiError
from api.movies import MoviesApi
from models.movie import Movie
from state.app_state import AppState
from widgets.movie_card import MovieCard
from typing import Callable


class MoviesView(ft.Column):
    def __init__(self, api_client: ApiClient, app_state: AppState, on_movie_click: Callable[[int], None]):
        self._api_client = api_client
        self._app_state = app_state
        self._on_movie_click = on_movie_click
        self._movies_api = MoviesApi(api_client)
        self._movies: list[Movie] = []
        self._skip = 0
        self._limit = 20
        self._loading = False

        self._search_field = ft.TextField(
            hint_text="Поиск фильма...",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._on_search,
            expand=True,
        )

        self._grid = ft.Row(
            wrap=True,
            spacing=12,
            run_spacing=12,
            alignment=ft.MainAxisAlignment.START,
        )

        self._progress = ft.ProgressBar(visible=False, bar_height=2)
        self._empty_text = ft.Text("Фильмы не найдены", size=16, color=ft.Colors.ON_SURFACE_VARIANT, visible=False)

        super().__init__(
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            controls=[
                ft.Container(
                    padding=ft.padding.Padding(16, 16, 16, 0),
                    content=ft.Row(
                        controls=[
                            ft.Text("Фильмы", size=24, weight=ft.FontWeight.BOLD),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ),
                ft.Container(
                    padding=ft.padding.Padding(16, 0, 16, 0),
                    content=self._search_field,
                ),
                self._progress,
                ft.Container(
                    padding=ft.padding.Padding(16, 0, 16, 0),
                    content=self._grid,
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
        self._load_movies()

    def _on_search(self, e):
        self._filter_movies()

    def _filter_movies(self):
        query = self._search_field.value.strip().lower()
        filtered = self._movies if not query else [
            m for m in self._movies
            if query in m.title.lower() or query in m.genre.lower()
        ]
        self._render_movies(filtered)

    def _load_movies(self):
        if self._loading:
            return
        self._loading = True
        self._progress.visible = True
        self.update()

        try:
            self._movies = self._movies_api.get_all(skip=0, limit=100)
            self._render_movies(self._movies)
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")
        except Exception as ex:
            self._show_snackbar(f"Ошибка подключения: {ex}")
        finally:
            self._loading = False
            self._progress.visible = False
            self.update()

    def _render_movies(self, movies: list[Movie]):
        self._grid.controls.clear()
        if not movies:
            self._empty_text.visible = True
        else:
            self._empty_text.visible = False
            for movie in movies:
                card = MovieCard(movie, on_click=self._on_movie_click)
                card.width = 200
                self._grid.controls.append(card)
        self.update()

    def _show_snackbar(self, msg: str):
        if self.page:
            sb = ft.SnackBar(ft.Text(msg))
            self.page.overlay.append(sb)
            sb.open = True
            self.page.update()
