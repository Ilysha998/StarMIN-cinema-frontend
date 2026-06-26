import flet as ft
from api.client import ApiClient, ApiError
from api.sessions import SessionsApi
from api.movies import MoviesApi
from api.halls import HallsApi
from models.session import Session, SessionCreate, SessionUpdate
from models.movie import Movie
from models.hall import Hall
from state.app_state import AppState
from typing import Dict


class AdminSessionsView(ft.Column):
    def __init__(self, api_client: ApiClient, app_state: AppState):
        self._api_client = api_client
        self._app_state = app_state
        self._sessions_api = SessionsApi(api_client)
        self._movies_api = MoviesApi(api_client)
        self._halls_api = HallsApi(api_client)
        self._sessions: list[Session] = []
        self._movies: list[Movie] = []
        self._halls: list[Hall] = []
        self._halls_map: Dict[int, str] = {}
        self._dialog = ft.AlertDialog()

        self._progress = ft.ProgressBar(visible=False, bar_height=2)
        self._table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Фильм")),
                ft.DataColumn(ft.Text("Дата/Время")),
                ft.DataColumn(ft.Text("Зал")),
                ft.DataColumn(ft.Text("Цена")),
                ft.DataColumn(ft.Text("Действия")),
            ],
            rows=[],
        )

        super().__init__(
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            controls=[
                ft.Container(
                    padding=ft.padding.Padding(16, 16, 16, 0),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Управление сеансами", size=24, weight=ft.FontWeight.BOLD),
                            ft.Button(
                                "Добавить сеанс",
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
        self._load_data()

    def _load_data(self):
        self._progress.visible = True
        self.update()

        try:
            self._movies = self._movies_api.get_all(skip=0, limit=100)
            self._sessions = self._sessions_api.get_all(skip=0, limit=100)
            self._halls = self._halls_api.get_all()
            self._halls_map = {h.id: h.name for h in self._halls}
            self._render()
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")
        except Exception as ex:
            self._show_snackbar(f"Ошибка подключения: {ex}")
        finally:
            self._progress.visible = False
            self.update()

    def _render(self):
        movies_map = {m.id: m for m in self._movies}
        self._table.rows.clear()
        for s in self._sessions:
            m = movies_map.get(s.movie_id)
            movie_title = m.title if m else f"#{s.movie_id}"
            dt_str = s.datetime.strftime("%d.%m.%Y %H:%M")
            hall_name = self._halls_map.get(s.hall_id, f"Зал {s.hall_id}")

            self._table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(s.id))),
                        ft.DataCell(ft.Text(movie_title, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)),
                        ft.DataCell(ft.Text(dt_str)),
                        ft.DataCell(ft.Text(hall_name)),
                        ft.DataCell(ft.Text(f"{int(s.price)} ₽")),
                        ft.DataCell(
                            ft.Row(spacing=4, controls=[
                                ft.IconButton(icon=ft.Icons.EDIT, icon_size=18, on_click=lambda e, session=s: self._show_edit_dialog(session)),
                                ft.IconButton(icon=ft.Icons.DELETE, icon_size=18, icon_color=ft.Colors.ERROR, on_click=lambda e, session=s: self._delete_session(session)),
                            ])
                        ),
                    ],
                )
            )
        self.update()

    def _show_add_dialog(self, e):
        movie_opts = {m.id: m.title for m in self._movies}
        movie_dd = ft.Dropdown(
            label="Фильм",
            options=[ft.dropdown.Option(key=str(mid), text=title) for mid, title in movie_opts.items()],
        )
        date_f = ft.TextField(label="Дата (YYYY-MM-DD)")
        time_f = ft.TextField(label="Время (HH:MM)")
        hall_dd = ft.Dropdown(
            label="Зал",
            options=[ft.dropdown.Option(key=str(h.id), text=h.name) for h in self._halls],
        )
        price_f = ft.TextField(label="Цена", keyboard_type=ft.KeyboardType.NUMBER)

        def submit(ee):
            try:
                from datetime import datetime
                dt = datetime.strptime(f"{date_f.value} {time_f.value}", "%Y-%m-%d %H:%M")
                sc = SessionCreate(
                    movie_id=int(movie_dd.value),
                    datetime=dt,
                    hall_id=int(hall_dd.value),
                    price=float(price_f.value),
                )
                self._sessions_api.create(sc)
                self._close_dialog()
                self._load_data()
                self._show_snackbar("Сеанс добавлен")
            except ApiError as ex:
                self._show_snackbar(f"Ошибка: {ex.detail}")
            except (ValueError, TypeError):
                self._show_snackbar("Неверные данные")

        self._dialog.content = ft.Container(
            padding=16,
            width=400,
            content=ft.Column([
                ft.Text("Новый сеанс", size=18, weight=ft.FontWeight.BOLD),
                movie_dd, date_f, time_f, hall_dd, price_f,
                ft.Row([
                    ft.Button("Создать", on_click=submit),
                    ft.OutlinedButton("Отмена", on_click=lambda _: self._close_dialog()),
                ], alignment=ft.MainAxisAlignment.END),
            ], tight=True, spacing=12),
        )
        self._dialog.open = True
        self.page.show_dialog(self._dialog)

    def _show_edit_dialog(self, session: Session):
        price_f = ft.TextField(label="Цена", value=str(int(session.price)), keyboard_type=ft.KeyboardType.NUMBER)

        def submit(ee):
            try:
                su = SessionUpdate(price=float(price_f.value))
                self._sessions_api.update(session.id, su)
                self._close_dialog()
                self._load_data()
                self._show_snackbar("Сеанс обновлён")
            except ApiError as ex:
                self._show_snackbar(f"Ошибка: {ex.detail}")
            except ValueError:
                self._show_snackbar("Неверная цена")

        self._dialog.content = ft.Container(
            padding=16,
            width=400,
            content=ft.Column([
                ft.Text(f"Редактирование сеанса #{session.id}", size=18, weight=ft.FontWeight.BOLD),
                price_f,
                ft.Row([
                    ft.Button("Сохранить", on_click=submit),
                    ft.OutlinedButton("Отмена", on_click=lambda _: self._close_dialog()),
                ], alignment=ft.MainAxisAlignment.END),
            ], tight=True, spacing=12),
        )
        self._dialog.open = True
        self.page.show_dialog(self._dialog)

    def _delete_session(self, session: Session):
        def confirm(ee):
            try:
                self._sessions_api.delete(session.id)
                self._close_dialog()
                self._load_data()
                self._show_snackbar("Сеанс удалён")
            except ApiError as ex:
                self._show_snackbar(f"Ошибка: {ex.detail}")

        self._dialog.content = ft.Container(
            padding=16,
            content=ft.Column([
                ft.Text(f"Удалить сеанс #{session.id}?", size=18),
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
