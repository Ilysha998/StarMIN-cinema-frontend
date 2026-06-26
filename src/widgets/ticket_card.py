import flet as ft
from typing import Callable, Optional, Dict
from utils.ticket_utils import generate_qr_bytes


class TicketCard(ft.Container):
    def __init__(self, ticket_data: dict, on_pay: Optional[Callable[[int], None]] = None, on_cancel: Optional[Callable[[int], None]] = None, on_download: Optional[Callable[[int], None]] = None, on_refund: Optional[Callable[[int], None]] = None):
        self.ticket_data = ticket_data
        self._on_pay = on_pay
        self._on_cancel = on_cancel
        self._on_download = on_download
        self._on_refund = on_refund

        tid = ticket_data.get("id", "?")
        movie_title = ticket_data.get("movie_title", "—")
        hall_name = ticket_data.get("hall_name") or f"Зал ?"
        seat_row = ticket_data.get("seat_row", 0)
        seat_col = ticket_data.get("seat_col", 0)
        seat_type = ticket_data.get("seat_type", "standard")
        price = ticket_data.get("price", 0)
        is_paid = ticket_data.get("is_paid", False)
        refunded = ticket_data.get("refunded", False)
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

        if refunded:
            paid_color = ft.Colors.RED
            paid_text = "Возвращён"

        seat_label = f"Ряд {seat_row + 1}, Место {seat_col + 1}"
        if seat_type == "sofa":
            seat_label += " (диван)"

        qr_image = ft.Container()
        if qr_token:
            try:
                qr_bytes = generate_qr_bytes(qr_token, size=200)
                qr_image = ft.Image(
                    src=qr_bytes,
                    width=120,
                    height=120,
                    fit=ft.BoxFit.CONTAIN,
                )
            except Exception:
                qr_image = ft.Text("Ошибка QR", size=10, color=ft.Colors.ERROR)

        action_controls = []
        if not is_paid and not refunded and self._on_pay:
            action_controls.append(
                ft.Button(
                    "Оплатить",
                    icon=ft.Icons.PAYMENT,
                    on_click=lambda _: self._on_pay(tid),
                    style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY),
                ),
            )
        if is_paid and not refunded and self._on_refund:
            action_controls.append(
                ft.Button(
                    "Вернуть деньги",
                    icon=ft.Icons.MONEY_OFF,
                    on_click=lambda _: self._on_refund(tid),
                    style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE, color=ft.Colors.ON_PRIMARY),
                ),
            )
        if self._on_download and not refunded:
            action_controls.append(
                ft.Button(
                    "Скачать билет",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=lambda _: self._on_download(tid),
                    style=ft.ButtonStyle(bgcolor=ft.Colors.SECONDARY, color=ft.Colors.ON_SECONDARY),
                ),
            )
        if self._on_cancel and not is_paid and not refunded:
            action_controls.append(
                ft.OutlinedButton(
                    "Отменить",
                    icon=ft.Icons.CANCEL,
                    on_click=lambda _: self._on_cancel(tid),
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
                        wrap=True,
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
                        wrap=True,
                        controls=[
                            ft.Row(spacing=4, controls=[
                                ft.Icon(ft.Icons.CHAIR, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Text(seat_label, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
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
                        content=ft.Column(spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                            ft.Row(spacing=4, controls=[
                                ft.Icon(ft.Icons.QR_CODE_2, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Text("QR-код для входа", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                            ]),
                            qr_image,
                        ]),
                    ) if qr_token else ft.Container(),
                ],
            ),
        )
