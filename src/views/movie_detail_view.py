import flet as ft
from api.client import ApiClient, ApiError
from api.movies import MoviesApi
from api.sessions import SessionsApi
from models.movie import Movie
from models.session import Session
from state.app_state import AppState
from widgets.session_card import SessionCard
from typing import Callable, Optional, Dict
from datetime import datetime, timedelta


AGE_COLORS = {
    0: ft.Colors.GREEN, 6: ft.Colors.BLUE, 12: ft.Colors.ORANGE,
    16: ft.Colors.DEEP_ORANGE, 18: ft.Colors.RED,
}


class MovieDetailView(ft.Column):
    def __init__(self, api_client: ApiClient, app_state: AppState, movie_id: int, on_session_click: Callable[[int], None], on_back: Callable, halls_map: Optional[Dict[int, str]] = None):
        self._api_client = api_client
        self._app_state = app_state
        self._movie_id = movie_id
        self._on_session_click = on_session_click
        self._on_back = on_back
        self._halls_map = halls_map or {}
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
        self._today_label = ft.Container()
        self._today_column = ft.Column(spacing=8)
        self._other_label = ft.Container()
        self._other_column = ft.Column(spacing=8)

        super().__init__(
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            controls=[
                ft.Container(
                    padding=16,
                    content=ft.Row(controls=[self._back_btn, ft.Text("Фильм", size=24, weight=ft.FontWeight.BOLD)]),
                ),
                self._progress,
                ft.Container(padding=ft.padding.Padding(16, 0, 16, 0), content=self._info_section),
                self._today_label,
                ft.Container(padding=ft.padding.Padding(16, 0, 16, 0), content=self._today_column),
                self._other_label,
                ft.Container(padding=ft.padding.Padding(16, 0, 16, 0), content=self._other_column),
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

        age_c = AGE_COLORS.get(m.age_restriction, ft.Colors.GREY)

        now = datetime.now()
        today = now.date()
        sessions_by_date: dict[object, list[Session]] = {}
        for s in self._sessions:
            d = s.datetime.date()
            sessions_by_date.setdefault(d, []).append(s)

        has_today = today in sessions_by_date
        active_today = []
        ended_today = []
        if has_today:
            for s in sessions_by_date[today]:
                session_end = s.datetime + timedelta(minutes=m.duration)
                if session_end > now:
                    active_today.append(s)
                else:
                    ended_today.append(s)

        today_status = ft.Container()
        if has_today:
            if active_today:
                today_status = ft.Container(
                    padding=ft.padding.Padding(6, 8, 6, 8),
                    border_radius=6,
                    bgcolor=ft.Colors.GREEN,
                    content=ft.Text(f"Сегодня — {len(active_today)} сеанс{'ов' if len(active_today) > 1 else ''}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_PRIMARY),
                )
            else:
                today_status = ft.Container(
                    padding=ft.padding.Padding(6, 8, 6, 8),
                    border_radius=6,
                    bgcolor=ft.Colors.ORANGE,
                    content=ft.Text("Сегодня — все сеансы завершены", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_PRIMARY),
                )
        else:
            today_status = ft.Container(
                padding=ft.padding.Padding(6, 8, 6, 8),
                border_radius=6,
                bgcolor=ft.Colors.SURFACE_CONTAINER,
                content=ft.Text("Сегодня сеансов нет", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            )

        self._info_section.content = ft.Column(
            spacing=12,
            controls=[
                ft.Container(
                    height=160,
                    border_radius=12,
                    alignment=ft.alignment.Alignment(0, 0),
                    content=ft.Stack(
                        controls=[
                            ft.Container(
                                bgcolor=ft.Colors.SURFACE_CONTAINER,
                                border_radius=12,
                                expand=True,
                            ),
                            ft.Image(
                                src=m.banner_url or m.poster_url,
                                fit=ft.controls.box.BoxFit.COVER,
                                border_radius=12,
                                expand=True,
                            ),
                        ],
                    ),
                ),
                ft.Text(m.title, size=24, weight=ft.FontWeight.BOLD),
                ft.Column(
                    spacing=4,
                    controls=[
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Container(
                                    padding=ft.padding.Padding(4, 8, 4, 8),
                                    border_radius=6,
                                    bgcolor=age_c,
                                    content=ft.Text(f"{m.age_restriction}+", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_PRIMARY),
                                ),
                                ft.Row(spacing=4, controls=[
                                    ft.Icon(ft.Icons.CATEGORY, size=16, color=ft.Colors.ON_SURFACE_VARIANT),
                                    ft.Text(m.genre, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                ]),
                                ft.Row(spacing=4, controls=[
                                    ft.Icon(ft.Icons.TIMER_OUTLINED, size=16, color=ft.Colors.ON_SURFACE_VARIANT),
                                    ft.Text(f"{m.duration} мин", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                ]),
                            ],
                        ),
                        today_status,
                    ],
                ),
            ],
        )

        self._today_column.controls.clear()
        self._other_column.controls.clear()
        self._today_label.content = ft.Container()
        self._other_label.content = ft.Container()

        if active_today:
            self._today_label.content = ft.Container(
                padding=ft.padding.Padding(16, 8, 16, 0),
                content=ft.Text("Сегодня — актуальные", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
            )
            active_today.sort(key=lambda s: s.datetime)
            for s in active_today:
                self._today_column.controls.append(
                    SessionCard(s, movie_title=m.title, halls_map=self._halls_map, on_click=self._on_session_click)
                )

        if ended_today:
            if active_today:
                self._today_column.controls.append(ft.Divider())
            self._today_column.controls.append(
                ft.Text("Завершённые", size=13, color=ft.Colors.ON_SURFACE_VARIANT)
            )
            ended_today.sort(key=lambda s: s.datetime)
            for s in ended_today:
                card = SessionCard(s, movie_title=m.title, halls_map=self._halls_map, on_click=None)
                card.opacity = 0.5
                self._today_column.controls.append(card)

        other_dates = sorted(d for d in sessions_by_date if d != today)
        if other_dates:
            self._other_label.content = ft.Container(
                padding=ft.padding.Padding(16, 8, 16, 0),
                content=ft.Text("Другие дни", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
            )
            for d in other_dates:
                self._other_column.controls.append(
                    ft.Text(d.strftime("%d %B"), size=14, weight=ft.FontWeight.W_500)
                )
                for s in sorted(sessions_by_date[d], key=lambda x: x.datetime):
                    self._other_column.controls.append(
                        SessionCard(s, movie_title=m.title, halls_map=self._halls_map, on_click=self._on_session_click)
                    )

    def _show_snackbar(self, msg: str):
        if self.page:
            sb = ft.SnackBar(ft.Text(msg))
            self.page.overlay.append(sb)
            sb.open = True
            self.page.update()
