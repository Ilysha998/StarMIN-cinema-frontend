import flet as ft
import io
from api.client import ApiClient, ApiError
from api.tickets import TicketsApi
from api.sessions import SessionsApi
from api.movies import MoviesApi
from api.halls import HallsApi
from state.app_state import AppState
from models.ticket import SalesStatistics


class AdminStatsView(ft.Column):
    def __init__(self, api_client: ApiClient, app_state: AppState):
        self._api_client = api_client
        self._app_state = app_state
        self._tickets_api = TicketsApi(api_client)
        self._sessions_api = SessionsApi(api_client)
        self._movies_api = MoviesApi(api_client)
        self._halls_api = HallsApi(api_client)
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
                            ft.Row(spacing=8, controls=[
                                ft.Button(
                                    "Экспорт Excel",
                                    icon=ft.Icons.TABLE_CHART,
                                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN, color=ft.Colors.ON_PRIMARY),
                                    on_click=lambda _: self._export_excel(),
                                ),
                                ft.Button(
                                    "Обновить",
                                    icon=ft.Icons.REFRESH,
                                    on_click=lambda _: self._load_stats(),
                                ),
                            ]),
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

    def _export_excel(self):
        self._progress.visible = True
        self.update()

        try:
            tickets = []
            skip = 0
            limit = 100
            while True:
                batch = self._tickets_api.get_all(is_paid=True, skip=skip, limit=limit)
                if not batch:
                    break
                tickets.extend(batch)
                if len(batch) < limit:
                    break
                skip += limit
            if not tickets:
                self._show_snackbar("Нет оплаченных билетов для экспорта")
                return

            session_ids = list({t.session_id for t in tickets})
            sessions_map = {}
            for sid in session_ids:
                try:
                    s = self._sessions_api.get_by_id(sid)
                    sessions_map[sid] = s
                except Exception:
                    pass

            movie_ids = list({s.movie_id for s in sessions_map.values()})
            movies_map = {}
            for mid in movie_ids:
                try:
                    m = self._movies_api.get_by_id(mid)
                    movies_map[mid] = m
                except Exception:
                    pass

            hall_ids = list({s.hall_id for s in sessions_map.values()})
            halls_map = {}
            for hid in hall_ids:
                try:
                    h = self._halls_api.get_by_id(hid)
                    halls_map[hid] = h
                except Exception:
                    pass

            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

            wb = Workbook()
            ws = wb.active
            ws.title = "Оплаченные билеты"

            headers = ["ID билета", "Дата покупки", "Зал", "Фильм", "Возраст+", "Цена"]
            header_font = Font(bold=True, color="FFFFFF", size=11)
            header_fill = PatternFill(start_color="3F51B5", end_color="3F51B5", fill_type="solid")
            header_align = Alignment(horizontal="center", vertical="center")
            thin_border = Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin"),
            )

            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_align
                cell.border = thin_border

            for row_idx, ticket in enumerate(tickets, 2):
                session = sessions_map.get(ticket.session_id)
                movie = movies_map.get(session.movie_id) if session else None
                hall = halls_map.get(session.hall_id) if session else None

                purchase_time = session.datetime.strftime("%d.%m.%Y %H:%M") if session else "—"
                hall_name = hall.name if hall else "—"
                movie_title = movie.title if movie else "—"
                age_restriction = f"{movie.age_restriction}+" if movie else "—"
                price = ticket.price

                row_data = [ticket.id, purchase_time, hall_name, movie_title, age_restriction, price]
                for col, value in enumerate(row_data, 1):
                    cell = ws.cell(row=row_idx, column=col, value=value)
                    cell.border = thin_border
                    if col == 6:
                        cell.number_format = '#,##0.00'
                        cell.alignment = Alignment(horizontal="right")

            ws.column_dimensions['A'].width = 10
            ws.column_dimensions['B'].width = 20
            ws.column_dimensions['C'].width = 15
            ws.column_dimensions['D'].width = 35
            ws.column_dimensions['E'].width = 12
            ws.column_dimensions['F'].width = 12

            buf = io.BytesIO()
            wb.save(buf)
            wb.close()
            buf.seek(0)

            import os
            save_dir = os.path.join(os.path.expanduser("~"), "Documents")
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, "starmin_paid_tickets.xlsx")
            with open(save_path, "wb") as f:
                f.write(buf.getvalue())

            self._show_snackbar(f"Экспортировано: {save_path}")

        except ImportError:
            self._show_snackbar("Ошибка: openpyxl не установлен")
        except ApiError as ex:
            self._show_snackbar(f"Ошибка API: {ex.detail}")
        except Exception as ex:
            self._show_snackbar(f"Ошибка: {ex}")
        finally:
            self._progress.visible = False
            self.update()

    def _show_snackbar(self, msg: str):
        if self.page:
            sb = ft.SnackBar(ft.Text(msg))
            self.page.overlay.append(sb)
            sb.open = True
            self.page.update()
