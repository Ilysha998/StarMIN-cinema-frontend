import flet as ft
from typing import List, Callable, Optional


HALL_ROWS = {"1": 10, "2": 8, "vip": 3}
HALL_COLS = {"1": 10, "2": 10, "vip": 10}


class SeatGrid(ft.Column):
    def __init__(
        self,
        hall: str,
        booked_seats: List[int],
        on_seat_select: Callable[[int], None],
        selected_seat: Optional[int] = None,
        available_width: int = 400,
    ):
        self.hall = hall
        self.booked_seats = set(booked_seats)
        self._on_seat_select = on_seat_select
        self._selected_seat = selected_seat

        rows = HALL_ROWS.get(hall, 10)
        cols = HALL_COLS.get(hall, 10)

        seat_spacing = 4
        seat_size = min(36, max(24, (available_width - 16 - (cols - 1) * seat_spacing) // cols))
        font_size = 10 if seat_size >= 30 else 8

        grid_rows = []
        seat_num = 1

        screen = ft.Container(
            alignment=ft.alignment.Alignment(0, 0),
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border_radius=8,
            padding=8,
            content=ft.Text("ЭКРАН", size=12, color=ft.Colors.ON_SURFACE_VARIANT, weight=ft.FontWeight.BOLD),
        )
        grid_rows.append(screen)
        grid_rows.append(ft.Divider(height=8, color=ft.Colors.TRANSPARENT))

        for row_idx in range(rows):
            row_controls = []
            for col_idx in range(cols):
                num = seat_num
                seat_num += 1
                is_booked = num in self.booked_seats
                is_selected = num == self._selected_seat

                if is_booked:
                    btn_bgcolor = ft.Colors.SURFACE_CONTAINER
                    btn_color = ft.Colors.ON_SURFACE_VARIANT
                    on_click = None
                elif is_selected:
                    btn_bgcolor = ft.Colors.PRIMARY
                    btn_color = ft.Colors.ON_PRIMARY
                    on_click = lambda e, n=num: self._select(n)
                else:
                    btn_bgcolor = ft.Colors.PRIMARY_CONTAINER
                    btn_color = ft.Colors.ON_PRIMARY_CONTAINER
                    on_click = lambda e, n=num: self._select(n)

                btn = ft.Container(
                    width=seat_size,
                    height=seat_size,
                    border_radius=6,
                    bgcolor=btn_bgcolor,
                    alignment=ft.alignment.Alignment(0, 0),
                    ink=on_click is not None,
                    on_click=on_click,
                    content=ft.Text(str(num), size=font_size, color=btn_color, text_align=ft.TextAlign.CENTER),
                )
                row_controls.append(btn)

            grid_rows.append(
                ft.Row(controls=row_controls, alignment=ft.MainAxisAlignment.CENTER, spacing=seat_spacing)
            )

        legend = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
            wrap=True,
            controls=[
                ft.Row(spacing=4, controls=[
                    ft.Container(width=16, height=16, border_radius=4, bgcolor=ft.Colors.PRIMARY_CONTAINER),
                    ft.Text("Свободно", size=12),
                ]),
                ft.Row(spacing=4, controls=[
                    ft.Container(width=16, height=16, border_radius=4, bgcolor=ft.Colors.PRIMARY),
                    ft.Text("Выбрано", size=12),
                ]),
                ft.Row(spacing=4, controls=[
                    ft.Container(width=16, height=16, border_radius=4, bgcolor=ft.Colors.SURFACE_CONTAINER),
                    ft.Text("Занято", size=12),
                ]),
            ],
        )

        inner_grid = ft.Column(spacing=4, controls=grid_rows)

        super().__init__(
            scroll=ft.ScrollMode.AUTO,
            spacing=4,
            controls=[
                ft.Row(scroll=ft.ScrollMode.AUTO, controls=[inner_grid]),
                ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                legend,
            ],
        )

    def _select(self, seat_num: int):
        self._selected_seat = seat_num
        self._on_seat_select(seat_num)
