import flet as ft
from api.client import ApiClient, ApiError
from api.sessions import SessionsApi
from api.tickets import TicketsApi
from api.movies import MoviesApi
from models.session import SessionWithTickets, Session
from models.movie import Movie
from models.ticket import AvailableSeats
from state.app_state import AppState
from widgets.seat_grid import SeatGrid
from typing import Callable, Optional


HALL_NAMES = {"1": "Зал 1", "2": "Зал 2", "vip": "VIP"}


class SessionDetailView(ft.Column):
    def __init__(
        self,
        api_client: ApiClient,
        app_state: AppState,
        session_id: int,
        on_back: Callable,
        on_ticket_bought: Optional[Callable] = None,
    ):
        self._api_client = api_client
        self._app_state = app_state
        self._session_id = session_id
        self._on_back = on_back
        self._on_ticket_bought = on_ticket_bought
        self._sessions_api = SessionsApi(api_client)
        self._tickets_api = TicketsApi(api_client)
        self._movies_api = MoviesApi(api_client)
        self._session: Optional[SessionWithTickets] = None
        self._movie: Optional[Movie] = None
        self._available: Optional[AvailableSeats] = None
        self._selected_seat: Optional[int] = None

        self._progress = ft.ProgressBar(visible=False, bar_height=2)
        self._info_section = ft.Container()
        self._seat_container = ft.Container()
        self._buy_btn = ft.Button(
            "Выберите место",
            icon=ft.Icons.CONFIRMATION_NUMBER,
            disabled=True,
            style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY),
        )

        super().__init__(
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            controls=[
                ft.Container(
                    padding=16,
                    content=ft.Row(controls=[
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: self._on_back()),
                        ft.Text("Выбор места", size=24, weight=ft.FontWeight.BOLD),
                    ]),
                ),
                self._progress,
                ft.Container(padding=ft.padding.Padding(16, 0, 16, 0), content=self._info_section),
                ft.Container(padding=ft.padding.Padding(16, 0, 16, 0), content=self._seat_container),
                ft.Container(
                    padding=16,
                    alignment=ft.alignment.Alignment(0, 0),
                    content=self._buy_btn,
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
            self._session = self._sessions_api.get_by_id(self._session_id)
            self._available = self._tickets_api.get_available_seats(self._session_id)
            try:
                self._movie = self._movies_api.get_by_id(self._session.movie_id)
            except Exception:
                self._movie = None
            self._render()
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")
        except Exception as ex:
            self._show_snackbar(f"Ошибка подключения: {ex}")
        finally:
            self._progress.visible = False
            self.update()

    def _render(self):
        s = self._session
        if not s or not self._available:
            return

        movie_title = self._movie.title if self._movie else f"Фильм #{s.movie_id}"
        hall_name = HALL_NAMES.get(s.hall, f"Зал {s.hall}")
        dt = s.datetime
        date_str = dt.strftime("%d %b %Y")
        time_str = dt.strftime("%H:%M")

        self._info_section.content = ft.Column(
            spacing=8,
            controls=[
                ft.Text(movie_title, size=22, weight=ft.FontWeight.BOLD),
                ft.Row(
                    spacing=16,
                    controls=[
                        ft.Row(spacing=4, controls=[
                            ft.Icon(ft.Icons.CALENDAR_TODAY, size=16, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(date_str, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                        ]),
                        ft.Row(spacing=4, controls=[
                            ft.Icon(ft.Icons.ACCESS_TIME, size=16, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(time_str, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                        ]),
                        ft.Row(spacing=4, controls=[
                            ft.Icon(ft.Icons.MEETING_ROOM, size=16, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(hall_name, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                        ]),
                        ft.Text(f"{int(s.price)} ₽", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                    ],
                ),
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.Text(f"Свободно: {self._available.available_count}", size=14, color=ft.Colors.GREEN),
                        ft.Text(f"Занято: {self._available.booked_count}", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text(f"Всего: {self._available.total_seats}", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                    ],
                ),
            ],
        )

        booked = [seat for seat in range(1, self._available.total_seats + 1) if seat not in self._available.available_seats]
        grid = SeatGrid(s.hall, booked, on_seat_select=self._on_seat_select)
        self._seat_container.content = grid
        self.update()

    def _on_seat_select(self, seat_num: int):
        self._selected_seat = seat_num
        self._buy_btn.text = f"Купить билет — место {seat_num} — {int(self._session.price)} ₽"
        self._buy_btn.disabled = False
        self._buy_btn.on_click = self._do_buy
        self.update()

    def _do_buy(self, e):
        if not self._selected_seat:
            return

        self._buy_btn.disabled = True
        self._buy_btn.text = "Покупка..."
        self.update()

        try:
            ticket = self._tickets_api.buy(self._session_id, self._selected_seat)
            self._show_snackbar(f"Билет куплен! Место {ticket.seat_number}")
            if self._on_ticket_bought:
                self._on_ticket_bought()
            self._on_back()
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")
            self._buy_btn.disabled = False
            self._buy_btn.text = f"Купить билет — место {self._selected_seat}"
            self.update()
        except Exception as ex:
            self._show_snackbar(f"Ошибка: {ex}")
            self._buy_btn.disabled = False
            self.update()

    def _show_snackbar(self, msg: str):
        if self.page:
            sb = ft.SnackBar(ft.Text(msg))
            self.page.overlay.append(sb)
            sb.open = True
            self.page.update()
