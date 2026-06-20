import flet as ft
from api.client import ApiClient, ApiError
from api.users import UsersApi
from models.user import User, UserUpdate
from state.app_state import AppState


class AdminUsersView(ft.Column):
    def __init__(self, api_client: ApiClient, app_state: AppState):
        self._api_client = api_client
        self._app_state = app_state
        self._users_api = UsersApi(api_client)
        self._users: list[User] = []
        self._dialog = ft.AlertDialog()

        self._progress = ft.ProgressBar(visible=False, bar_height=2)
        self._table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Логин")),
                ft.DataColumn(ft.Text("Админ")),
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
                    content=ft.Text("Пользователи", size=24, weight=ft.FontWeight.BOLD),
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
        self._load_users()

    def _load_users(self):
        self._progress.visible = True
        self.update()

        try:
            self._users = self._users_api.get_all(skip=0, limit=100)
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
        for u in self._users:
            self._table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(u.id))),
                        ft.DataCell(ft.Text(u.login)),
                        ft.DataCell(ft.Text("Да" if u.is_admin else "Нет")),
                        ft.DataCell(
                            ft.Row(spacing=4, controls=[
                                ft.IconButton(
                                    icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                                    icon_size=18,
                                    on_click=lambda e, user=u: self._toggle_admin(user),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    icon_size=18,
                                    icon_color=ft.Colors.ERROR,
                                    on_click=lambda e, user=u: self._delete_user(user),
                                ),
                            ])
                        ),
                    ],
                )
            )
        self.update()

    def _toggle_admin(self, user: User):
        try:
            self._users_api.update(user.id, UserUpdate(is_admin=not user.is_admin))
            self._load_users()
            self._show_snackbar(f"Роль изменена для {user.login}")
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")

    def _delete_user(self, user: User):
        if user.id == self._app_state.current_user.id:
            self._show_snackbar("Нельзя удалить самого себя")
            return

        def confirm(ee):
            try:
                self._users_api.delete(user.id)
                self._close_dialog()
                self._load_users()
                self._show_snackbar("Пользователь удалён")
            except ApiError as ex:
                self._show_snackbar(f"Ошибка: {ex.detail}")

        self._dialog.content = ft.Container(
            padding=16,
            content=ft.Column([
                ft.Text(f"Удалить пользователя \"{user.login}\"?", size=18),
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
