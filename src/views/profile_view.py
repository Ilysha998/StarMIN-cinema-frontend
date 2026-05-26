import flet as ft
from api.client import ApiClient, ApiError
from api.auth import AuthApi
from api.users import UsersApi
from state.app_state import AppState
from typing import Callable


class ProfileView(ft.Column):
    def __init__(self, api_client: ApiClient, app_state: AppState, on_logout: Callable, on_theme_change: Callable, on_url_change: Callable):
        self._api_client = api_client
        self._app_state = app_state
        self._on_logout = on_logout
        self._on_theme_change = on_theme_change
        self._on_url_change = on_url_change
        self._users_api = UsersApi(api_client)

        self._old_pass = ft.TextField(label="Текущий пароль", password=True, can_reveal_password=True)
        self._new_pass = ft.TextField(label="Новый пароль", password=True, can_reveal_password=True)
        self._pass_status = ft.Text("", size=13)

        self._url_field = ft.TextField(
            label="URL сервера",
            value=self._api_client.base_url,
            on_submit=self._change_url,
        )

        user = self._app_state.current_user

        super().__init__(
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            controls=[
                ft.Container(
                    padding=ft.padding.Padding(16, 16, 16, 0),
                    content=ft.Text("Профиль", size=24, weight=ft.FontWeight.BOLD),
                ),
                ft.Container(
                    padding=16,
                    content=ft.Card(
                        content=ft.Container(
                            padding=16,
                            content=ft.Column(
                                spacing=12,
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=48),
                                            ft.Column([
                                                ft.Text(user.login if user else "—", size=20, weight=ft.FontWeight.BOLD),
                                                ft.Text("Администратор" if (user and user.is_admin) else "Пользователь", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                            ]),
                                        ],
                                    ),
                                    ft.Divider(),
                                    ft.Text("Смена пароля", size=16, weight=ft.FontWeight.W_500),
                                    self._old_pass,
                                    self._new_pass,
                                    self._pass_status,
                                    ft.Button(
                                        "Сменить пароль",
                                        icon=ft.Icons.LOCK_RESET,
                                        on_click=self._change_password,
                                    ),
                                    ft.Divider(),
                                    ft.Text("Настройки", size=16, weight=ft.FontWeight.W_500),
                                    ft.Row([
                                        ft.Icon(ft.Icons.DARK_MODE, size=20),
                                        ft.Text("Тёмная тема", size=14, expand=True),
                                        ft.Switch(on_change=lambda e: self.page.run_task(self._on_theme_change, e.control.value)),
                                    ]),
                                    self._url_field,
                                    ft.Button(
                                        "Применить URL",
                                        icon=ft.Icons.SAVE,
                                        on_click=lambda _: self._change_url(None),
                                    ),
                                    ft.Divider(),
                                    ft.OutlinedButton(
                                        "Выйти",
                                        icon=ft.Icons.LOGOUT,
                                        on_click=lambda _: self.page.run_task(self._on_logout),
                                        #color=ft.Colors.ERROR,
                                    ),
                                ],
                            ),
                        ),
                    ),
                ),
            ],
            expand=True,
        )

    def _change_password(self, e):
        old = self._old_pass.value
        new = self._new_pass.value
        if not old or not new:
            self._pass_status.value = "Заполните оба поля"
            self._pass_status.color = ft.Colors.ERROR
            self.update()
            return
        if len(new) < 6:
            self._pass_status.value = "Новый пароль минимум 6 символов"
            self._pass_status.color = ft.Colors.ERROR
            self.update()
            return

        try:
            self._users_api.change_password(self._app_state.current_user.id, old, new)
            self._pass_status.value = "Пароль изменён!"
            self._pass_status.color = ft.Colors.GREEN
            self._old_pass.value = ""
            self._new_pass.value = ""
        except ApiError as ex:
            self._pass_status.value = ex.detail
            self._pass_status.color = ft.Colors.ERROR
        except Exception as ex:
            self._pass_status.value = f"Ошибка: {ex}"
            self._pass_status.color = ft.Colors.ERROR
        self.update()

    def _change_url(self, e):
        url = self._url_field.value.strip()
        if url:
            self._api_client.set_base_url(url)
            self.page.run_task(self._on_url_change, url)
            self._show_snackbar(f"URL изменён на {url}")

    def _show_snackbar(self, msg: str):
        if self.page:
            sb = ft.SnackBar(ft.Text(msg))
            self.page.overlay.append(sb)
            sb.open = True
            self.page.update()
