import flet as ft
from api.client import ApiClient, ApiError
from api.sessions import SessionsApi
from api.tickets import TicketsApi
from api.movies import MoviesApi
from api.halls import HallsApi
from models.session import SessionWithTickets
from models.movie import Movie
from models.ticket import SeatMap, Ticket, TicketUpdate
from models.hall import Hall
from state.app_state import AppState
from widgets.seat_grid import SeatGrid
from utils.ticket_utils import generate_qr_bytes, generate_ticket_pdf
from typing import Callable, Optional, Dict, List
from datetime import datetime as _dt
import re


STEP_SEAT = 0
STEP_CONTACT = 1
STEP_PAYMENT = 2
STEP_RESULT = 3


class SessionDetailView(ft.Column):
    def __init__(
        self,
        api_client: ApiClient,
        app_state: AppState,
        session_id: int,
        halls_map: Optional[Dict[int, str]] = None,
        on_back: Callable = None,
        on_ticket_bought: Optional[Callable] = None,
    ):
        self._api_client = api_client
        self._app_state = app_state
        self._session_id = session_id
        self._halls_map = halls_map or {}
        self._on_back = on_back
        self._on_ticket_bought = on_ticket_bought
        self._sessions_api = SessionsApi(api_client)
        self._tickets_api = TicketsApi(api_client)
        self._movies_api = MoviesApi(api_client)
        self._halls_api = HallsApi(api_client)
        self._session: Optional[SessionWithTickets] = None
        self._movie: Optional[Movie] = None
        self._seat_map: Optional[SeatMap] = None
        self._hall: Optional[Hall] = None
        self._selected_seats: List[tuple] = []
        self._current_step = STEP_SEAT
        self._bought_tickets: List[Ticket] = []

        self._progress = ft.ProgressBar(visible=False, bar_height=2)

        self._stepper = ft.Row(spacing=0, alignment=ft.MainAxisAlignment.CENTER, scroll=ft.ScrollMode.ADAPTIVE)

        self._step_content = ft.Container(padding=ft.padding.Padding(16, 0, 16, 16))

        self._phone_raw = ""
        self._phone_field = ft.TextField(
            label="Телефон",
            prefix_icon=ft.Icons.PHONE,
            hint_text="+7 (___) ___-__-__",
            keyboard_type=ft.KeyboardType.PHONE,
            on_change=self._on_phone_change,
            max_length=18,
        )
        self._email_field = ft.TextField(
            label="Email",
            prefix_icon=ft.Icons.EMAIL,
            hint_text="mail@example.com",
            keyboard_type=ft.KeyboardType.EMAIL,
            on_change=self._on_email_change,
        )
        self._contact_error = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)

        super().__init__(
            scroll=ft.ScrollMode.AUTO,
            spacing=0,
            controls=[
                ft.Container(
                    padding=16,
                    content=ft.Row(controls=[
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: self._go_back()),
                        ft.Text("Оформление билета", size=22, weight=ft.FontWeight.BOLD),
                    ]),
                ),
                self._progress,
                ft.Container(padding=ft.padding.Padding(16, 0, 16, 8), content=self._stepper),
                ft.Divider(height=1),
                self._step_content,
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
            self._seat_map = self._tickets_api.get_seat_map(self._session_id)
            try:
                self._hall = self._halls_api.get_by_id(self._session.hall_id)
                self._halls_map[self._hall.id] = self._hall.name
            except Exception:
                self._hall = None
            try:
                self._movie = self._movies_api.get_by_id(self._session.movie_id)
            except Exception:
                self._movie = None
            self._render_step()
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")
        except Exception as ex:
            self._show_snackbar(f"Ошибка подключения: {ex}")
        finally:
            self._progress.visible = False
            self.update()

    def _go_back(self):
        if self._current_step > STEP_SEAT and self._current_step < STEP_RESULT:
            self._current_step -= 1
            self._render_step()
            self.update()
        else:
            self._on_back()

    def _build_stepper(self):
        labels = ["Место", "Контакты", "Оплата", "Билет"]
        icons = [ft.Icons.EVENT_SEAT, ft.Icons.CONTACTS, ft.Icons.PAYMENT, ft.Icons.CONFIRMATION_NUMBER]
        controls = []
        for i, (label, icon) in enumerate(zip(labels, icons)):
            is_active = i == self._current_step
            is_done = i < self._current_step
            if is_done:
                bg = ft.Colors.PRIMARY
                fg = ft.Colors.ON_PRIMARY
            elif is_active:
                bg = ft.Colors.PRIMARY_CONTAINER
                fg = ft.Colors.ON_PRIMARY_CONTAINER
            else:
                bg = ft.Colors.SURFACE_CONTAINER
                fg = ft.Colors.ON_SURFACE_VARIANT

            chip = ft.Container(
                padding=ft.padding.Padding(10, 6, 10, 6),
                border_radius=20,
                bgcolor=bg,
                content=ft.Row(spacing=4, controls=[
                    ft.Icon(icon if not is_done else ft.Icons.CHECK, size=14, color=fg),
                    ft.Text(label, size=11, color=fg, weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL),
                ]),
            )
            controls.append(chip)
            if i < len(labels) - 1:
                controls.append(ft.Container(
                    width=24,
                    height=2,
                    bgcolor=ft.Colors.PRIMARY if is_done or is_active else ft.Colors.SURFACE_CONTAINER,
                    alignment=ft.alignment.Alignment(0, 0),
                    border_radius=1,
                ))
        self._stepper.controls = controls

    def _render_step(self):
        self._build_stepper()

        if self._current_step == STEP_SEAT:
            self._render_seat_step()
        elif self._current_step == STEP_CONTACT:
            self._render_contact_step()
        elif self._current_step == STEP_PAYMENT:
            self._render_payment_step()
        elif self._current_step == STEP_RESULT:
            self._render_result_step()

        self.update()

    def _get_hall_name(self, hall_id: int) -> str:
        if self._seat_map and self._seat_map.hall_name:
            return self._seat_map.hall_name
        return self._halls_map.get(hall_id, f"Зал {hall_id}")

    def _session_info_row(self) -> ft.Column:
        s = self._session
        movie_title = self._movie.title if self._movie else f"Фильм #{s.movie_id}"
        hall_name = self._get_hall_name(s.hall_id)
        dt = s.datetime
        date_str = dt.strftime("%d %b %Y")
        time_str = dt.strftime("%H:%M")

        return ft.Column(spacing=4, controls=[
            ft.Text(movie_title, size=18, weight=ft.FontWeight.BOLD),
            ft.Row(spacing=16, wrap=True, controls=[
                ft.Row(spacing=4, controls=[
                    ft.Icon(ft.Icons.CALENDAR_TODAY, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(date_str, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                ]),
                ft.Row(spacing=4, controls=[
                    ft.Icon(ft.Icons.ACCESS_TIME, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(time_str, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                ]),
                ft.Row(spacing=4, controls=[
                    ft.Icon(ft.Icons.MEETING_ROOM, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(hall_name, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                ]),
                ft.Text(f"{int(s.price)} ₽", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
            ]),
        ])

    def _calc_total(self) -> float:
        if not self._seat_map or not self._selected_seats:
            return 0.0
        total = 0.0
        for r, c in self._selected_seats:
            cell = self._seat_map.seat_map[r][c]
            mult = 1.5 if cell.type == "sofa" else 1.0
            total += self._session.price * mult
        return total

    def _render_seat_step(self):
        s = self._session
        if not s or not self._seat_map:
            return

        started = s.datetime <= _dt.now()

        info = self._session_info_row()

        if started:
            info.controls.append(
                ft.Container(
                    padding=ft.padding.Padding(8, 8, 8, 8),
                    border_radius=8,
                    bgcolor=ft.Colors.ERROR_CONTAINER,
                    content=ft.Row(spacing=6, controls=[
                        ft.Icon(ft.Icons.EVENT_BUSY, size=16, color=ft.Colors.ON_ERROR_CONTAINER),
                        ft.Text("Сеанс уже начался — покупка недоступна", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_ERROR_CONTAINER),
                    ]),
                )
            )
            self._step_content.content = ft.Column(spacing=12, controls=[info])
            return

        sm = self._seat_map
        seats_info = ft.Row(spacing=12, controls=[
            ft.Text(f"Свободно: {sm.available_count}", size=13, color=ft.Colors.GREEN),
            ft.Text(f"Занято: {sm.booked_count}", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
        ])

        grid_w = int(self.page.width) - 48 if self.page else 400
        grid = SeatGrid(sm, on_seats_change=self._on_seats_change, selected_seats=self._selected_seats, available_width=grid_w)

        n = len(self._selected_seats)
        total = self._calc_total()
        next_label = f"Далее ({n} {self._seat_word(n)}, {int(total)} ₽)" if n else "Выберите места"
        next_btn = ft.Button(
            next_label,
            icon=ft.Icons.ARROW_FORWARD,
            disabled=n == 0,
            style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY),
            on_click=lambda _: self._go_to_contact() if self._selected_seats else None,
        )

        self._step_content.content = ft.Column(spacing=12, controls=[
            info,
            seats_info,
            grid,
            ft.Container(padding=8, alignment=ft.alignment.Alignment(1, 0), content=next_btn),
        ])

    @staticmethod
    def _seat_word(n: int) -> str:
        if n % 10 == 1 and n % 100 != 11:
            return "место"
        elif 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
            return "места"
        return "мест"

    def _on_seats_change(self, seats: List[tuple]):
        self._selected_seats = seats
        self._render_seat_step()

    def _go_to_contact(self):
        self._current_step = STEP_CONTACT
        self._render_step()

    def _render_contact_step(self):
        info = self._session_info_row()
        total = self._calc_total()
        seats_desc = ", ".join(
            f"Ряд {r+1}, Место {c+1}" for r, c in self._selected_seats
        )
        seat_text = f"{seats_desc} — {int(total)} ₽"

        if self._selected_seats and self._seat_map:
            for r, c in self._selected_seats:
                cell = self._seat_map.seat_map[r][c]
                if cell.type == "sofa":
                    seat_text += " (диван)"
                    break

        logged_in = self._app_state.is_logged_in
        if logged_in:
            user = self._app_state.current_user
            phone_val = getattr(user, 'phone', '') or ''
            email_val = getattr(user, 'email', '') or ''
            self._phone_raw = re.sub(r"\D", "", phone_val)
            self._phone_field.value = self._format_phone(self._phone_raw) if self._phone_raw else ""
            self._email_field.value = email_val
        else:
            self._phone_field.value = ""
            self._email_field.value = ""

        self._contact_error.visible = False

        form = ft.Column(spacing=12, controls=[
            ft.Text("Контактные данные", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("Для связи и получения билета. Хотя бы одно поле обязательно." if not logged_in else "Данные из профиля заполнены автоматически.", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            self._phone_field,
            self._email_field,
            self._contact_error,
            ft.Row(spacing=8, controls=[
                ft.OutlinedButton("Назад", icon=ft.Icons.ARROW_BACK, on_click=lambda _: self._go_back()),
                ft.Button(
                    "К оплате",
                    icon=ft.Icons.PAYMENT,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY),
                    on_click=self._validate_contact,
                ),
            ]),
        ])

        self._step_content.content = ft.Column(spacing=12, controls=[
            info,
            ft.Divider(height=1),
            ft.Container(
                padding=ft.padding.Padding(12, 8, 12, 8),
                border_radius=8,
                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                content=ft.Row(spacing=6, controls=[
                    ft.Icon(ft.Icons.EVENT_SEAT, size=16, color=ft.Colors.ON_PRIMARY_CONTAINER),
                    ft.Text(seat_text, size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_PRIMARY_CONTAINER),
                ]),
            ),
            form,
        ])

    def _format_phone(self, raw: str) -> str:
        raw = raw[:11]
        if len(raw) == 0:
            return ""
        elif len(raw) == 1:
            return f"+{raw}"
        elif len(raw) <= 4:
            return f"+{raw[0]} ({raw[1:]}"
        elif len(raw) <= 7:
            return f"+{raw[0]} ({raw[1:4]}) {raw[4:]}"
        elif len(raw) <= 9:
            return f"+{raw[0]} ({raw[1:4]}) {raw[4:7]}-{raw[7:]}"
        else:
            return f"+{raw[0]} ({raw[1:4]}) {raw[4:7]}-{raw[7:9]}-{raw[9:]}"

    def _on_phone_change(self, e):
        new_digits = re.sub(r"\D", "", self._phone_field.value or "")
        if new_digits.startswith("8"):
            new_digits = "7" + new_digits[1:]
        if new_digits and not new_digits.startswith("7"):
            new_digits = "7" + new_digits
        new_digits = new_digits[:11]
        self._phone_raw = new_digits
        formatted = self._format_phone(new_digits)
        self._phone_field.value = formatted
        self._phone_field.update()

    def _get_raw_phone(self) -> str:
        return self._phone_raw

    def _is_phone_valid(self) -> bool:
        return len(self._phone_raw) == 11

    def _is_email_valid(self) -> bool:
        val = (self._email_field.value or "").strip()
        if not val:
            return False
        return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", val))

    def _on_email_change(self, e):
        val = (self._email_field.value or "").strip()
        if val and not self._is_email_valid():
            self._email_field.error_text = "Неверный формат email"
        else:
            self._email_field.error_text = ""
        self._email_field.update()

    def _validate_contact(self, e=None):
        phone_raw = self._get_raw_phone()
        email = (self._email_field.value or "").strip()

        has_phone = len(phone_raw) == 11
        has_email = bool(email) and self._is_email_valid()

        if not self._app_state.is_logged_in and not has_phone and not has_email:
            self._contact_error.value = "Укажите хотя бы телефон или email"
            self._contact_error.visible = True
            self.update()
            return

        if phone_raw and not has_phone:
            self._contact_error.value = "Телефон: 11 цифр в формате +7 (XXX) XXX-XX-XX"
            self._contact_error.visible = True
            self.update()
            return

        if email and not has_email:
            self._contact_error.value = "Неверный формат email"
            self._contact_error.visible = True
            self.update()
            return

        self._contact_error.visible = False
        self._current_step = STEP_PAYMENT
        self._render_step()

    def _render_payment_step(self):
        info = self._session_info_row()
        s = self._session
        hall_name = self._get_hall_name(s.hall_id)
        total = self._calc_total()

        phone = f"+{self._get_raw_phone()}" if self._is_phone_valid() else "—"
        email = (self._email_field.value or "").strip() if self._is_email_valid() else "—"

        seat_rows = []
        for r, c in self._selected_seats:
            cell = self._seat_map.seat_map[r][c]
            label = f"Ряд {r+1}, Место {c+1}"
            if cell.type == "sofa":
                label += " (диван)"
            mult = 1.5 if cell.type == "sofa" else 1.0
            seat_price = s.price * mult
            seat_rows.append(ft.Row(spacing=8, controls=[
                ft.Icon(ft.Icons.EVENT_SEAT, size=16, color=ft.Colors.PRIMARY),
                ft.Text(f"{label} — {int(seat_price)} ₽", size=14),
            ]))

        summary = ft.Container(
            padding=16,
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            content=ft.Column(spacing=8, controls=[
                ft.Text("Итого к оплате", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                *seat_rows,
                ft.Row(spacing=8, controls=[
                    ft.Icon(ft.Icons.MEETING_ROOM, size=16, color=ft.Colors.PRIMARY),
                    ft.Text(hall_name, size=14),
                ]),
                ft.Row(spacing=8, controls=[
                    ft.Icon(ft.Icons.PHONE, size=16, color=ft.Colors.PRIMARY),
                    ft.Text(phone, size=14),
                ]),
                ft.Row(spacing=8, controls=[
                    ft.Icon(ft.Icons.EMAIL, size=16, color=ft.Colors.PRIMARY),
                    ft.Text(email, size=14),
                ]),
                ft.Divider(height=1),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Text("К оплате:", size=16, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{int(total)} ₽", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                ]),
            ]),
        )

        pay_btn = ft.Button(
            f"Оплатить {int(total)} ₽",
            icon=ft.Icons.PAYMENT,
            style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY),
            on_click=self._do_buy,
        )

        self._step_content.content = ft.Column(spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            info,
            ft.Divider(height=1),
            ft.Container(width=min(400, int(self.page.width * 0.9)) if self.page else 400, content=summary),
            ft.Row(spacing=8, controls=[
                ft.OutlinedButton("Назад", icon=ft.Icons.ARROW_BACK, on_click=lambda _: self._go_back()),
                pay_btn,
            ]),
        ])

    def _do_buy(self, e):
        if not self._selected_seats:
            return

        phone = f"+{self._get_raw_phone()}" if self._is_phone_valid() else None
        email = (self._email_field.value or "").strip() or None
        if email and not self._is_email_valid():
            email = None

        self._progress.visible = True
        self.update()

        try:
            tickets = self._tickets_api.buy(
                self._session_id,
                seats=self._selected_seats,
                phone=phone,
                email=email,
            )
            for t in tickets:
                if not t.is_paid:
                    self._tickets_api.update(t.id, TicketUpdate(is_paid=True))
            self._bought_tickets = tickets
            if self._on_ticket_bought:
                self._on_ticket_bought()
            self._current_step = STEP_RESULT
            self._render_step()
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")
        except Exception as ex:
            self._show_snackbar(f"Ошибка: {ex}")
        finally:
            self._progress.visible = False
            self.update()

    def _render_result_step(self):
        if not self._bought_tickets:
            return

        s = self._session
        movie_title = self._movie.title if self._movie else f"Фильм #{s.movie_id}"
        hall_name = self._get_hall_name(s.hall_id)
        dt = s.datetime
        date_str = dt.strftime("%d %b %Y")
        time_str = dt.strftime("%H:%M")

        ticket_cards = []
        for ticket in self._bought_tickets:
            seat_label = f"Ряд {ticket.seat_row + 1}, Место {ticket.seat_col + 1}"
            if ticket.seat_type == "sofa":
                seat_label += " (диван)"

            qr_control = ft.Container()
            if ticket.qr_token:
                try:
                    qr_bytes = generate_qr_bytes(ticket.qr_token, size=300)
                    qr_control = ft.Image(
                        src=qr_bytes,
                        width=160,
                        height=160,
                        fit=ft.BoxFit.CONTAIN,
                    )
                except Exception:
                    pass

            ticket_cards.append(ft.Container(
                padding=12,
                border_radius=12,
                bgcolor=ft.Colors.SURFACE_CONTAINER,
                content=ft.Column(
                    spacing=4,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(spacing=16, controls=[
                            ft.Row(spacing=4, controls=[
                                ft.Icon(ft.Icons.EVENT_SEAT, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Text(seat_label, size=13),
                            ]),
                            ft.Text(f"{int(ticket.price)} ₽", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                        ]),
                        qr_control,
                    ],
                ),
            ))

        header = ft.Column(
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text("Билеты куплены!", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN),
                ft.Divider(height=1),
                ft.Text(movie_title, size=16, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Row(spacing=16, controls=[
                    ft.Row(spacing=4, controls=[
                        ft.Icon(ft.Icons.CALENDAR_TODAY, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text(date_str, size=13),
                    ]),
                    ft.Row(spacing=4, controls=[
                        ft.Icon(ft.Icons.ACCESS_TIME, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text(time_str, size=13),
                    ]),
                ]),
                ft.Row(spacing=16, controls=[
                    ft.Row(spacing=4, controls=[
                        ft.Icon(ft.Icons.MEETING_ROOM, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text(hall_name, size=13),
                    ]),
                    ft.Text(f"{len(self._bought_tickets)} {self._seat_word(len(self._bought_tickets))}", size=14, weight=ft.FontWeight.BOLD),
                ]),
            ],
        )

        total_price = sum(t.price for t in self._bought_tickets)

        async def _save_pdf(e):
            try:
                for ticket in self._bought_tickets:
                    seat_label = f"Ряд {ticket.seat_row + 1}, Место {ticket.seat_col + 1}"
                    pdf_bytes = generate_ticket_pdf(
                        movie_title=movie_title,
                        date_str=date_str,
                        time_str=time_str,
                        hall=hall_name,
                        seat_row=ticket.seat_row + 1,
                        seat_col=ticket.seat_col + 1,
                        price=ticket.price,
                        qr_token=ticket.qr_token,
                        is_paid=ticket.is_paid,
                        phone=ticket.phone,
                        email=ticket.email,
                    )
                    import os
                    save_dir = os.path.join(os.path.expanduser("~"), "Documents")
                    os.makedirs(save_dir, exist_ok=True)
                    save_path = os.path.join(save_dir, f"ticket_{ticket.id}.pdf")
                    with open(save_path, "wb") as f:
                        f.write(pdf_bytes)
                self._show_snackbar(f"Сохранено в Documents")
            except Exception as ex:
                self._show_snackbar(f"Ошибка: {ex}")

        self._step_content.content = ft.Column(
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    padding=20,
                    border_radius=16,
                    bgcolor=ft.Colors.SURFACE_CONTAINER,
                    width=min(420, int(self.page.width * 0.85)) if self.page else 420,
                    content=ft.Column(
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            header,
                            ft.Divider(height=1),
                            *ticket_cards,
                        ],
                    ),
                ),
                ft.Row(spacing=8, alignment=ft.MainAxisAlignment.CENTER, controls=[
                    ft.Button(
                        "Сохранить PDF",
                        icon=ft.Icons.PICTURE_AS_PDF,
                        style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY),
                        on_click=lambda e: self.page.run_task(_save_pdf, e),
                    ),
                    ft.OutlinedButton("На главную", icon=ft.Icons.HOME, on_click=lambda _: self._on_back()),
                ]),
            ],
        )

    def _show_snackbar(self, msg: str):
        if self.page:
            sb = ft.SnackBar(ft.Text(msg))
            self.page.overlay.append(sb)
            sb.open = True
            self.page.update()
