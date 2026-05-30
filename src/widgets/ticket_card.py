import flet as ft
from typing import Callable, Optional


HALL_NAMES = {"1": "Зал 1", "2": "Зал 2", "vip": "VIP"}


class TicketCard(ft.Container):
    def __init__(self, ticket_data: dict, on_pay: Optional[Callable[[int], None]] = None, on_cancel: Optional[Callable[[int], None]] = None):
        self.ticket_data = ticket_data
        self._on_pay = on_pay
        self._on_cancel = on_cancel

        tid = ticket_data.get("id", "?")
        movie_title = ticket_data.get("movie_title", "—")
        hall = ticket_data.get("hall", "?")
        hall_name = HALL_NAMES.get(hall, f"Зал {hall}")
        seat = ticket_data.get("seat_number", "?")
        price = ticket_data.get("price", 0)
        is_paid = ticket_data.get("is_paid", False)
        dt_str = ticket_data.get("session_datetime", "")
        qr_token = ticket_data.get("qr_token", "")

        date_display = ""
        time_display = ""
        if dt_str:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(dt_str)
                date_display = dt.strftime("%d %b %Y")
                time_display = dt.strftime("%H:%M")
            except (ValueError, TypeError):
                date_display = dt_str

        paid_color = ft.Colors.GREEN if is_paid else ft.Colors.ORANGE
        paid_text = "Оплачен" if is_paid else "Не оплачен"

        action_controls = []
        if not is_paid and self._on_pay:
            action_controls.append(
                ft.Button(
                    "Оплатить",
                    icon=ft.Icons.PAYMENT,
                    on_click=lambda _: self._on_pay(tid),
                    style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY),
                ),
            )
        if self._on_cancel:
            action_controls.append(
                ft.OutlinedButton(
                    "Отменить",
                    icon=ft.Icons.CANCEL,
                    on_click=lambda _: self._on_cancel(tid),
                    #color=ft.Colors.ERROR,
                ),
            )

        super().__init__(
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            padding=16,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(movie_title, size=16, weight=ft.FontWeight.BOLD, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Container(
                                padding=ft.padding.Padding(4, 10, 4, 10),
                                border_radius=6,
                                bgcolor=paid_color,
                                content=ft.Text(paid_text, size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_PRIMARY),
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=16,
                        controls=[
                            ft.Row(spacing=4, controls=[
                                ft.Icon(ft.Icons.CALENDAR_TODAY, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Text(date_display, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                            ]),
                            ft.Row(spacing=4, controls=[
                                ft.Icon(ft.Icons.ACCESS_TIME, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Text(time_display, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                            ]),
                        ],
                    ),
                    ft.Row(
                        spacing=16,
                        controls=[
                            ft.Row(spacing=4, controls=[
                                ft.Icon(ft.Icons.CHAIR, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Text(f"Место {seat}", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                            ]),
                            ft.Row(spacing=4, controls=[
                                ft.Icon(ft.Icons.MEETING_ROOM, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Text(hall_name, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                            ]),
                            ft.Text(f"{int(price)} ₽", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                        ],
                    ),
                    ft.Row(spacing=8, controls=action_controls) if action_controls else ft.Container(),
                    ft.Container(
                        padding=8,
                        border_radius=6,
                        bgcolor=ft.Colors.SURFACE_CONTAINER,
                        visible=bool(qr_token),
                        content=ft.Column(spacing=4, controls=[
                            ft.Row(spacing=4, controls=[
                                ft.Icon(ft.Icons.QR_CODE_2, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Text("QR-код:", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                            ]),
                            ft.Text(qr_token or "", size=10, color=ft.Colors.ON_SURFACE_VARIANT, selectable=True, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ]),
                    ) if qr_token else ft.Container(),
                ],
            ),
        )
