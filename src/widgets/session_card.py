import flet as ft
from models.session import Session
from typing import Callable, Optional, Dict


class SessionCard(ft.Container):
    def __init__(self, session: Session, movie_title: Optional[str] = None, halls_map: Optional[Dict[int, str]] = None, on_click: Optional[Callable[[int], None]] = None):
        self.session = session
        self._on_click = on_click

        dt = session.datetime
        time_str = dt.strftime("%H:%M")
        date_str = dt.strftime("%d %b")

        hall_name = (halls_map or {}).get(session.hall_id, f"Зал {session.hall_id}")
        hall_color = ft.Colors.PRIMARY

        super().__init__(
            ink=True,
            on_click=lambda _: self._on_click(self.session.id) if self._on_click else None,
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            padding=16,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text(
                                movie_title or f"Фильм #{session.movie_id}",
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Row(
                                spacing=12,
                                wrap=True,
                                controls=[
                                    ft.Row(spacing=4, controls=[
                                        ft.Icon(ft.Icons.CALENDAR_TODAY, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                        ft.Text(date_str, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                                    ]),
                                    ft.Row(spacing=4, controls=[
                                        ft.Icon(ft.Icons.ACCESS_TIME, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                        ft.Text(time_str, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                                    ]),
                                    ft.Row(controls=[
                                        ft.Container(
                                            padding=ft.padding.Padding(6, 8, 6, 8),
                                            border_radius=6,
                                            bgcolor=hall_color,
                                            content=ft.Text(hall_name, size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_PRIMARY),
                                        ),
                                    ]),
                                ],
                            ),
                        ],
                    ),
                    ft.Text(f"{int(session.price)} ₽", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                ],
            ),
        )
