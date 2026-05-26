import flet as ft
from api.client import ApiClient, ApiError
from api.tickets import TicketsApi
from state.app_state import AppState
from widgets.ticket_card import TicketCard
from typing import Optional


class TicketsView(ft.Column):
    def __init__(self, api_client: ApiClient, app_state: AppState):
        self._api_client = api_client
        self._app_state = app_state
        self._tickets_api = TicketsApi(api_client)

        self._progress = ft.ProgressBar(visible=False, bar_height=2)
        self._tickets_column = ft.Column(spacing=12)
        self._empty_text = ft.Text("У вас нет билетов", size=16, color=ft.Colors.ON_SURFACE_VARIANT, visible=False)

        super().__init__(
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            controls=[
                ft.Container(
                    padding=ft.padding.Padding(16, 16, 16, 0),
                    content=ft.Text("Мои билеты", size=24, weight=ft.FontWeight.BOLD),
                ),
                self._progress,
                ft.Container(
                    padding=ft.padding.Padding(16, 0, 16, 0),
                    content=self._tickets_column,
                ),
                ft.Container(
                    padding=16,
                    alignment=ft.alignment.Alignment(0, 0),
                    content=self._empty_text,
                ),
            ],
            expand=True,
        )

    def did_mount(self):
        self._load_tickets()

    def _load_tickets(self):
        if not self._app_state.is_logged_in:
            return

        self._progress.visible = True
        self.update()

        try:
            tickets = self._tickets_api.get_my_enriched()
            self._render(tickets)
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")
        except Exception as ex:
            self._show_snackbar(f"Ошибка подключения: {ex}")
        finally:
            self._progress.visible = False
            self.update()

    def _render(self, tickets: list):
        self._tickets_column.controls.clear()
        if not tickets:
            self._empty_text.visible = True
        else:
            self._empty_text.visible = False
            for t in tickets:
                card = TicketCard(t, on_pay=self._pay_ticket, on_cancel=self._cancel_ticket)
                self._tickets_column.controls.append(card)
        self.update()

    def _pay_ticket(self, ticket_id: int):
        try:
            from models.ticket import TicketUpdate
            self._tickets_api.update(ticket_id, TicketUpdate(is_paid=True))
            self._show_snackbar("Билет оплачен!")
            self._load_tickets()
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")

    def _cancel_ticket(self, ticket_id: int):
        try:
            self._tickets_api.cancel(ticket_id)
            self._show_snackbar("Билет отменён")
            self._load_tickets()
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")

    def _show_snackbar(self, msg: str):
        if self.page:
            sb = ft.SnackBar(ft.Text(msg))
            self.page.overlay.append(sb)
            sb.open = True
            self.page.update()
