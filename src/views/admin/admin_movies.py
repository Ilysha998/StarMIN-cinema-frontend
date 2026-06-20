import flet as ft
from api.client import ApiClient, ApiError
from api.movies import MoviesApi
from models.movie import Movie, MovieCreate, MovieUpdate
from state.app_state import AppState


class AdminMoviesView(ft.Column):
    def __init__(self, api_client: ApiClient, app_state: AppState):
        self._api_client = api_client
        self._app_state = app_state
        self._movies_api = MoviesApi(api_client)
        self._movies: list[Movie] = []

        self._progress = ft.ProgressBar(visible=False, bar_height=2)
        self._table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Название")),
                ft.DataColumn(ft.Text("Жанр")),
                ft.DataColumn(ft.Text("Длительность")),
                ft.DataColumn(ft.Text("Возраст")),
                ft.DataColumn(ft.Text("Действия")),
            ],
            rows=[],
        )
        self._dialog = ft.AlertDialog()

        super().__init__(
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            controls=[
                ft.Container(
                    padding=ft.padding.Padding(16, 16, 16, 0),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Управление фильмами", size=24, weight=ft.FontWeight.BOLD),
                            ft.Button(
                                "Добавить фильм",
                                icon=ft.Icons.ADD,
                                on_click=self._show_add_dialog,
                            ),
                        ],
                    ),
                ),
                self._progress,
                ft.Container(
                    padding=16,
                    content=ft.Row(
                        controls=[self._table],
                        scroll=ft.ScrollMode.ALWAYS,
                        expand=True,
                    ),
                ),
            ],
            expand=True,
        )

    def did_mount(self):
        self._load_movies()

    def _load_movies(self):
        self._progress.visible = True
        self.update()

        try:
            self._movies = self._movies_api.get_all(skip=0, limit=100)
            self._render()
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")
        except Exception as ex:
            self._show_snackbar(f"Ошибка подключения: {ex}")
        finally:
            self._progress.visible = False
            self.update()

    def _render(self):
        self._table.rows.clear()
        for m in self._movies:
            self._table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(m.id))),
                        ft.DataCell(ft.Text(m.title, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)),
                        ft.DataCell(ft.Text(m.genre)),
                        ft.DataCell(ft.Text(f"{m.duration} мин")),
                        ft.DataCell(ft.Text(f"{m.age_restriction}+")),
                        ft.DataCell(
                            ft.Row(spacing=4, controls=[
                                ft.IconButton(icon=ft.Icons.EDIT, icon_size=18, on_click=lambda e, movie=m: self._show_edit_dialog(movie)),
                                ft.IconButton(icon=ft.Icons.DELETE, icon_size=18, icon_color=ft.Colors.ERROR, on_click=lambda e, movie=m: self._delete_movie(movie)),
                            ])
                        ),
                    ],
                )
            )
        self.update()

    def _show_add_dialog(self, e):
        title_f = ft.TextField(label="Название")
        genre_f = ft.TextField(label="Жанр")
        duration_f = ft.TextField(label="Длительность (мин)", keyboard_type=ft.KeyboardType.NUMBER)
        age_f = ft.TextField(label="Возрастное ограничение", keyboard_type=ft.KeyboardType.NUMBER)
        poster_f = ft.TextField(label="URL постера (необязательно)")

        def submit(ee):
            try:
                mc = MovieCreate(
                    title=title_f.value, genre=genre_f.value,
                    duration=int(duration_f.value), age_restriction=int(age_f.value),
                    poster_url=poster_f.value or None,
                )
                self._movies_api.create(mc)
                self._close_dialog()
                self._load_movies()
                self._show_snackbar("Фильм добавлен")
            except ApiError as ex:
                self._show_snackbar(f"Ошибка: {ex.detail}")
            except ValueError:
                self._show_snackbar("Неверные числовые значения")

        self._dialog.content = ft.Container(
            padding=16,
            width=400,
            content=ft.Column([
                ft.Text("Новый фильм", size=18, weight=ft.FontWeight.BOLD),
                title_f, genre_f, duration_f, age_f, poster_f,
                ft.Row([
                    ft.Button("Создать", on_click=submit),
                    ft.OutlinedButton("Отмена", on_click=lambda _: self._close_dialog()),
                ], alignment=ft.MainAxisAlignment.END),
            ], tight=True, spacing=12),
        )
        self._dialog.open = True
        self.page.show_dialog(self._dialog)

    def _show_edit_dialog(self, movie: Movie):
        title_f = ft.TextField(label="Название", value=movie.title)
        genre_f = ft.TextField(label="Жанр", value=movie.genre)
        duration_f = ft.TextField(label="Длительность (мин)", value=str(movie.duration))
        age_f = ft.TextField(label="Возрастное ограничение", value=str(movie.age_restriction))
        poster_f = ft.TextField(label="URL постера", value=movie.poster_url or "")

        def submit(ee):
            try:
                mu = MovieUpdate(
                    title=title_f.value, genre=genre_f.value,
                    duration=int(duration_f.value), age_restriction=int(age_f.value),
                    poster_url=poster_f.value or None,
                )
                self._movies_api.update(movie.id, mu)
                self._close_dialog()
                self._load_movies()
                self._show_snackbar("Фильм обновлён")
            except ApiError as ex:
                self._show_snackbar(f"Ошибка: {ex.detail}")
            except ValueError:
                self._show_snackbar("Неверные числовые значения")

        self._dialog.content = ft.Container(
            padding=16,
            width=400,
            content=ft.Column([
                ft.Text(f"Редактирование #{movie.id}", size=18, weight=ft.FontWeight.BOLD),
                title_f, genre_f, duration_f, age_f, poster_f,
                ft.Row([
                    ft.Button("Сохранить", on_click=submit),
                    ft.OutlinedButton("Отмена", on_click=lambda _: self._close_dialog()),
                ], alignment=ft.MainAxisAlignment.END),
            ], tight=True, spacing=12),
        )
        self._dialog.open = True
        self.page.show_dialog(self._dialog)

    def _delete_movie(self, movie: Movie):
        def confirm(ee):
            try:
                self._movies_api.delete(movie.id)
                self._close_dialog()
                self._load_movies()
                self._show_snackbar("Фильм удалён")
            except ApiError as ex:
                self._show_snackbar(f"Ошибка: {ex.detail}")

        self._dialog.content = ft.Container(
            padding=16,
            content=ft.Column([
                ft.Text(f"Удалить фильм \"{movie.title}\"?", size=18),
                ft.Row([
                    ft.Button("Удалить", on_click=confirm, style=ft.ButtonStyle(bgcolor=ft.Colors.ERROR, color=ft.Colors.ON_ERROR)),
                    ft.OutlinedButton("Отмена", on_click=lambda _: self._close_dialog()),
                ], alignment=ft.MainAxisAlignment.END),
            ], tight=True, spacing=12),
        )
        self._dialog.open = True
        self.page.show_dialog(self._dialog)

    def _close_dialog(self):
        self._dialog.open = False
        self.page.update()

    def _show_snackbar(self, msg: str):
        if self.page:
            sb = ft.SnackBar(ft.Text(msg))
            self.page.overlay.append(sb)
            sb.open = True
            self.page.update()
