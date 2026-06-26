import flet as ft
from api.client import ApiClient, ApiError
from api.auth import AuthApi
from state.app_state import AppState
from typing import Callable


class LoginView(ft.Column):
    def __init__(self, api_client: ApiClient, app_state: AppState, on_login: Callable, on_skip: Callable | None = None, on_url_change: Callable | None = None):
        self._api_client = api_client
        self._app_state = app_state
        self._on_login = on_login
        self._on_skip = on_skip
        self._on_url_change = on_url_change
        self._auth_api = AuthApi(api_client)

        self._login_field = ft.TextField(
            label="Логин",
            prefix_icon=ft.Icons.PERSON,
            autofocus=True,
        )
        self._password_field = ft.TextField(
            label="Пароль",
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
        )
        self._reg_login_field = ft.TextField(label="Логин", prefix_icon=ft.Icons.PERSON)
        self._reg_password_field = ft.TextField(label="Пароль", prefix_icon=ft.Icons.LOCK, password=True, can_reveal_password=True)
        self._reg_email_field = ft.TextField(label="Email", prefix_icon=ft.Icons.EMAIL)
        self._reg_phone_field = ft.TextField(label="Телефон", prefix_icon=ft.Icons.PHONE)
        self._is_admin_check = ft.Checkbox(label="Администратор", value=False)
        self._status_text = ft.Text("", color=ft.Colors.ERROR, size=13)
        self._loading = ft.ProgressBar(visible=False, bar_height=2)

        self._url_field = ft.TextField(
            label="URL сервера",
            value=self._api_client.base_url,
            on_submit=self._change_url,
            prefix_icon=ft.Icons.SETTINGS,
        )

        self._login_form = ft.Column(spacing=12, controls=[
            ft.Text("Вход", size=24, weight=ft.FontWeight.BOLD),
            self._login_field,
            self._password_field,
            self._status_text,
            ft.Button("Войти", icon=ft.Icons.LOGIN, on_click=self._do_login,
                      style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY)),
            ft.TextButton("Нет аккаунта? Зарегистрироваться", on_click=lambda _: self._show_register()),
            ft.Divider(),
            ft.Text("Настройки", size=16, weight=ft.FontWeight.W_500),
            self._url_field,
            ft.Button(
                "Применить URL",
                icon=ft.Icons.SAVE,
                on_click=lambda _: self._change_url(None),
            ),
            ft.Divider(),
            ft.TextButton("Продолжить без входа", icon=ft.Icons.VISIBILITY_OFF, on_click=lambda _: self._do_skip()),
        ])

        self._register_form = ft.Column(spacing=12, controls=[
            ft.Text("Регистрация", size=24, weight=ft.FontWeight.BOLD),
            self._reg_login_field,
            self._reg_password_field,
            self._reg_email_field,
            self._reg_phone_field,
            self._is_admin_check,
            self._status_text,
            ft.Button("Зарегистрироваться", icon=ft.Icons.PERSON_ADD, on_click=self._do_register,
                      style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY)),
            ft.TextButton("Уже есть аккаунт? Войти", on_click=lambda _: self._show_login()),
        ])

        self._card = ft.Container(
            width=400,
            padding=24,
            border_radius=16,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            content=self._login_form,
        )

        super().__init__(
            controls=[
                self._loading,
                ft.Container(
                    alignment=ft.alignment.Alignment(0, 0),
                    expand=True,
                    content=self._card,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )

    def _show_login(self):
        self._status_text.value = ""
        self._card.content = self._login_form
        self.update()

    def _show_register(self):
        self._status_text.value = ""
        self._card.content = self._register_form
        self.update()

    def _do_skip(self):
        if self._on_skip:
            self._on_skip()

    def _change_url(self, e):
        url = self._url_field.value.strip()
        if url:
            self._api_client.set_base_url(url)
            if self._on_url_change:
                self.page.run_task(self._on_url_change, url)
            self._show_snackbar(f"URL изменён на {url}")

    def _show_snackbar(self, msg: str):
        if self.page:
            sb = ft.SnackBar(ft.Text(msg))
            self.page.overlay.append(sb)
            sb.open = True
            self.page.update()

    def _show_loading(self, show: bool):
        self._loading.visible = show
        self.update()

    def _do_login(self, e):
        login = self._login_field.value.strip()
        password = self._password_field.value
        if not login or not password:
            self._status_text.value = "Введите логин и пароль"
            self._status_text.color = ft.Colors.ERROR
            self.update()
            return

        self._show_loading(True)
        self._status_text.value = ""
        self.update()

        try:
            token_resp = self._auth_api.login(login, password)
            self._api_client.token = token_resp.access_token
            user = self._auth_api.get_me()
            self._app_state.set_auth(token_resp.access_token, user)
            self.page.run_task(self._on_login)
        except ApiError as ex:
            self._status_text.value = ex.detail
            self._status_text.color = ft.Colors.ERROR
        except Exception as ex:
            self._status_text.value = f"Ошибка подключения: {ex}"
            self._status_text.color = ft.Colors.ERROR
        finally:
            self._show_loading(False)
            self.update()

    def _do_register(self, e):
        login = self._reg_login_field.value.strip()
        password = self._reg_password_field.value
        if not login or not password:
            self._status_text.value = "Введите логин и пароль"
            self._status_text.color = ft.Colors.ERROR
            self.update()
            return
        if len(password) < 6:
            self._status_text.value = "Пароль минимум 6 символов"
            self._status_text.color = ft.Colors.ERROR
            self.update()
            return

        phone = self._reg_phone_field.value.strip() or None
        email = self._reg_email_field.value.strip() or None

        self._show_loading(True)
        self._status_text.value = ""
        self.update()

        try:
            self._auth_api.register(login, password, self._is_admin_check.value, phone=phone, email=email)
            self._status_text.value = "Успешно! Войдите."
            self._status_text.color = ft.Colors.GREEN
            self._card.content = self._login_form
            self._login_field.value = login
        except ApiError as ex:
            self._status_text.value = ex.detail
            self._status_text.color = ft.Colors.ERROR
        except Exception as ex:
            self._status_text.value = f"Ошибка подключения: {ex}"
            self._status_text.color = ft.Colors.ERROR
        finally:
            self._show_loading(False)
            self.update()
