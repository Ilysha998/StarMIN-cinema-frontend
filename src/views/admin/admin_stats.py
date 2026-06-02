import flet as ft
from api.client import ApiClient, ApiError
from api.tickets import TicketsApi
from state.app_state import AppState
from models.ticket import SalesStatistics


class AdminStatsView(ft.Column):
    def __init__(self, api_client: ApiClient, app_state: AppState):
        self._api_client = api_client
        self._app_state = app_state
        self._tickets_api = TicketsApi(api_client)
        self._stats: SalesStatistics | None = None

        self._progress = ft.ProgressBar(visible=False, bar_height=2)
        self._stats_container = ft.Container()

        super().__init__(
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            controls=[
                ft.Container(
                    padding=ft.padding.Padding(16, 16, 16, 0),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Статистика продаж", size=24, weight=ft.FontWeight.BOLD),
                            ft.Button(
                                "Обновить",
                                icon=ft.Icons.REFRESH,
                                on_click=lambda _: self._load_stats(),
                            ),
                        ],
                    ),
                ),
                self._progress,
                ft.Container(
                    padding=16,
                    content=self._stats_container,
                ),
            ],
            expand=True,
        )

    def did_mount(self):
        self._load_stats()

    def _load_stats(self):
        self._progress.visible = True
        self.update()

        try:
            self._stats = self._tickets_api.get_sales_statistics()
            self._render()
        except ApiError as ex:
            self._show_snackbar(f"Ошибка: {ex.detail}")
        except Exception as ex:
            self._show_snackbar(f"Ошибка подключения: {ex}")
        finally:
            self._progress.visible = False
            self.update()

    def _render(self):
        s = self._stats
        if not s:
            return

        def stat_card(icon, label, value, color):
            return ft.Container(
                border_radius=12,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                padding=20,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                    controls=[
                        ft.Icon(icon, size=32, color=color),
                        ft.Text(str(value), size=28, weight=ft.FontWeight.BOLD),
                        ft.Text(label, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                    ],
                ),
            )

        self._stats_container.content = ft.Column(
            spacing=16,
            controls=[
                ft.ResponsiveRow(
                    spacing=12,
                    controls=[
                        ft.Container(col={"xs": 6, "sm": 4}, content=stat_card(ft.Icons.CONFIRMATION_NUMBER, "Всего билетов", s.total_tickets_sold, ft.Colors.PRIMARY)),
                        ft.Container(col={"xs": 6, "sm": 4}, content=stat_card(ft.Icons.PAID, "Оплачено", s.paid_tickets, ft.Colors.GREEN)),
                        ft.Container(col={"xs": 6, "sm": 4}, content=stat_card(ft.Icons.MONEY_OFF, "Не оплачено", s.unpaid_tickets, ft.Colors.ORANGE)),
                    ],
                ),
                ft.ResponsiveRow(
                    spacing=12,
                    controls=[
                        ft.Container(col={"xs": 6, "sm": 4}, content=stat_card(ft.Icons.THEATERS, "Всего сеансов", s.total_sessions, ft.Colors.BLUE)),
                        ft.Container(col={"xs": 6, "sm": 4}, content=stat_card(ft.Icons.PERCENT, "% оплаты", f"{s.payment_percentage}%", ft.Colors.TEAL)),
                        ft.Container(col={"xs": 6, "sm": 4}, content=stat_card(ft.Icons.ANALYTICS, "Среднее/сеанс", s.average_tickets_per_session, ft.Colors.PURPLE)),
                    ],
                ),
            ],
        )
        self.update()

    def _show_snackbar(self, msg: str):
        if self.page:
            sb = ft.SnackBar(ft.Text(msg))
            self.page.overlay.append(sb)
            sb.open = True
            self.page.update()
