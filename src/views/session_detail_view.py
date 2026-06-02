import flet as ft
from api.client import ApiClient, ApiError
from api.sessions import SessionsApi
from api.tickets import TicketsApi
from api.movies import MoviesApi
from models.session import SessionWithTickets
from models.movie import Movie
from models.ticket import AvailableSeats, Ticket, TicketUpdate
from state.app_state import AppState
from widgets.seat_grid import SeatGrid
from utils.ticket_utils import generate_qr_bytes, generate_ticket_pdf
from typing import Callable, Optional
from datetime import datetime as _dt
import re


HALL_NAMES = {"1": "Зал 1", "2": "Зал 2", "vip": "VIP"}

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
        self._current_step = STEP_SEAT
        self._bought_ticket: Optional[Ticket] = None

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
            self._available = self._tickets_api.get_available_seats(self._session_id)
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

    def _session_info_row(self) -> ft.Column:
        s = self._session
        movie_title = self._movie.title if self._movie else f"Фильм #{s.movie_id}"
        hall_name = HALL_NAMES.get(s.hall, f"Зал {s.hall}")
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

    def _render_seat_step(self):
        s = self._session
        if not s or not self._available:
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

        seats_info = ft.Row(spacing=12, controls=[
            ft.Text(f"Свободно: {self._available.available_count}", size=13, color=ft.Colors.GREEN),
            ft.Text(f"Занято: {self._available.booked_count}", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
        ])

        booked = [seat for seat in range(1, self._available.total_seats + 1) if seat not in self._available.available_seats]
        grid_w = int(self.page.width) - 48 if self.page else 400
        grid = SeatGrid(s.hall, booked, on_seat_select=self._on_seat_select, selected_seat=self._selected_seat, available_width=grid_w)

        next_btn = ft.Button(
            "Далее" if self._selected_seat else "Выберите место",
            icon=ft.Icons.ARROW_FORWARD,
            disabled=self._selected_seat is None,
            style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY),
            on_click=lambda _: self._go_to_contact() if self._selected_seat else None,
        )

        self._step_content.content = ft.Column(spacing=12, controls=[
            info,
            seats_info,
            grid,
            ft.Container(padding=8, alignment=ft.alignment.Alignment(1, 0), content=next_btn),
        ])

    def _on_seat_select(self, seat_num: int):
        self._selected_seat = seat_num
        self._render_seat_step()

    def _go_to_contact(self):
        self._current_step = STEP_CONTACT
        self._render_step()

    def _render_contact_step(self):
        info = self._session_info_row()
        seat_text = f"Место {self._selected_seat} — {int(self._session.price)} ₽"

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
        hall_name = HALL_NAMES.get(s.hall, f"Зал {s.hall}")

        phone = f"+{self._get_raw_phone()}" if self._is_phone_valid() else "—"
        email = (self._email_field.value or "").strip() if self._is_email_valid() else "—"

        summary = ft.Container(
            padding=16,
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            content=ft.Column(spacing=8, controls=[
                ft.Text("Итого к оплате", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Row(spacing=8, controls=[
                    ft.Icon(ft.Icons.EVENT_SEAT, size=16, color=ft.Colors.PRIMARY),
                    ft.Text(f"Место {self._selected_seat}", size=14),
                ]),
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
                    ft.Text(f"{int(s.price)} ₽", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                ]),
            ]),
        )

        pay_btn = ft.Button(
            f"Оплатить {int(s.price)} ₽",
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
        if not self._selected_seat:
            return

        phone = f"+{self._get_raw_phone()}" if self._is_phone_valid() else None
        email = (self._email_field.value or "").strip() or None
        if email and not self._is_email_valid():
            email = None

        self._progress.visible = True
        self.update()

        try:
            ticket = self._tickets_api.buy(self._session_id, self._selected_seat, phone=phone, email=email)
            paid_ticket = self._tickets_api.update(ticket.id, TicketUpdate(is_paid=True))
            self._bought_ticket = paid_ticket
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
        ticket = self._bought_ticket
        if not ticket:
            return

        s = self._session
        movie_title = self._movie.title if self._movie else f"Фильм #{s.movie_id}"
        hall_name = HALL_NAMES.get(s.hall, f"Зал {s.hall}")
        dt = s.datetime
        date_str = dt.strftime("%d %b %Y")
        time_str = dt.strftime("%H:%M")

        qr_control = ft.Container()
        if ticket.qr_token:
            try:
                qr_bytes = generate_qr_bytes(ticket.qr_token, size=300)
                qr_control = ft.Image(
                    src=qr_bytes,
                    width=220,
                    height=220,
                    fit=ft.BoxFit.CONTAIN,
                )
            except Exception:
                pass

        ticket_card = ft.Container(
            padding=20,
            border_radius=16,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            width=min(420, int(self.page.width * 0.85)) if self.page else 420,
            content=ft.Column(
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("Билет куплен!", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN),
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
                        ft.Row(spacing=4, controls=[
                            ft.Icon(ft.Icons.EVENT_SEAT, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(f"Место {ticket.seat_number}", size=13),
                        ]),
                    ]),
                    ft.Text(f"{int(s.price)} ₽", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                    ft.Divider(height=1),
                    qr_control,
                ],
            ),
        )

        async def _save_pdf(e):
            try:
                pdf_bytes = generate_ticket_pdf(
                    movie_title=movie_title,
                    date_str=date_str,
                    time_str=time_str,
                    hall=hall_name,
                    seat=ticket.seat_number,
                    price=s.price,
                    qr_token=ticket.qr_token or "",
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
                self._show_snackbar(f"Сохранено: {save_path}")
                try:
                    await self.page.launch_url(save_path)
                except Exception:
                    pass
            except Exception as ex:
                self._show_snackbar(f"Ошибка: {ex}")

        self._step_content.content = ft.Column(
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ticket_card,
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
