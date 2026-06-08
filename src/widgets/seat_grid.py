import flet as ft
from typing import Callable, Optional, List, Set
from models.ticket import SeatMap, SeatMapCell


class SeatGrid(ft.Column):
    def __init__(
        self,
        seat_map: SeatMap,
        on_seats_change: Callable[[List[tuple]], None],
        selected_seats: Optional[List[tuple]] = None,
        available_width: int = 400,
    ):
        self._seat_map = seat_map
        self._on_seats_change = on_seats_change
        self._selected_seats: Set[tuple] = set(selected_seats or [])

        rows = len(seat_map.seat_map)
        cols = len(seat_map.seat_map[0]) if rows else 0

        seat_spacing = 4
        seat_size = min(36, max(24, (available_width - 16 - (cols - 1) * seat_spacing) // cols))
        font_size = 10 if seat_size >= 30 else 8

        grid_rows = []

        screen = ft.Container(
            alignment=ft.alignment.Alignment(0, 0),
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border_radius=8,
            padding=8,
            content=ft.Text("ЭКРАН", size=12, color=ft.Colors.ON_SURFACE_VARIANT, weight=ft.FontWeight.BOLD),
        )
        grid_rows.append(screen)
        grid_rows.append(ft.Divider(height=8, color=ft.Colors.TRANSPARENT))

        type_colors = {
            "standard": ft.Colors.PRIMARY_CONTAINER,
            "sofa": "#FCE4EC",
        }
        type_selected = {
            "standard": ft.Colors.PRIMARY,
            "sofa": "#C62828",
        }

        for row_idx in range(rows):
            row_controls = []
            for col_idx in range(cols):
                cell: SeatMapCell = seat_map.seat_map[row_idx][col_idx]
                is_empty = cell.type == "empty" or cell.status == "none"
                is_booked = not is_empty and cell.status == "booked"
                is_selected = (row_idx, col_idx) in self._selected_seats
                stype = cell.type

                if is_empty:
                    btn = ft.Container(width=seat_size, height=seat_size)
                elif is_booked:
                    btn = ft.Container(
                        width=seat_size,
                        height=seat_size,
                        border_radius=6,
                        bgcolor=ft.Colors.SURFACE_CONTAINER,
                        alignment=ft.alignment.Alignment(0, 0),
                        content=ft.Text(f"{row_idx + 1},{col_idx + 1}", size=font_size, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                    )
                elif is_selected:
                    btn = ft.Container(
                        width=seat_size,
                        height=seat_size,
                        border_radius=6,
                        bgcolor=type_selected.get(stype, ft.Colors.PRIMARY),
                        alignment=ft.alignment.Alignment(0, 0),
                        ink=True,
                        on_click=lambda e, r=row_idx, c=col_idx: self._toggle(r, c),
                        content=ft.Text(f"{row_idx + 1},{col_idx + 1}", size=font_size, color=ft.Colors.ON_PRIMARY, text_align=ft.TextAlign.CENTER),
                    )
                else:
                    btn = ft.Container(
                        width=seat_size,
                        height=seat_size,
                        border_radius=6,
                        bgcolor=type_colors.get(stype, ft.Colors.PRIMARY_CONTAINER),
                        alignment=ft.alignment.Alignment(0, 0),
                        ink=True,
                        on_click=lambda e, r=row_idx, c=col_idx: self._toggle(r, c),
                        content=ft.Text(f"{row_idx + 1},{col_idx + 1}", size=font_size, color=ft.Colors.ON_PRIMARY_CONTAINER, text_align=ft.TextAlign.CENTER),
                    )
                row_controls.append(btn)

            grid_rows.append(
                ft.Row(controls=row_controls, alignment=ft.MainAxisAlignment.CENTER, spacing=seat_spacing)
            )

        legend_items = [
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
        ]

        has_sofa = any(
            cell.type == "sofa"
            for row in seat_map.seat_map
            for cell in row
            if cell.type and cell.type != "empty"
        )
        if has_sofa:
            legend_items.append(ft.Row(spacing=4, controls=[
                ft.Container(width=16, height=16, border_radius=4, bgcolor="#FCE4EC"),
                ft.Text("Диван", size=12),
            ]))

        legend = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
            wrap=True,
            controls=legend_items,
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

    def _toggle(self, row: int, col: int):
        key = (row, col)
        if key in self._selected_seats:
            self._selected_seats.discard(key)
        else:
            self._selected_seats.add(key)
        self._on_seats_change(list(self._selected_seats))
