import flet as ft
from models.movie import Movie
from typing import Callable


class MovieCard(ft.Container):
    def __init__(self, movie: Movie, on_click: Callable[[int], None]):
        self.movie = movie
        self._on_click = on_click

        age_badge_color = {
            0: ft.Colors.GREEN,
            6: ft.Colors.BLUE,
            12: ft.Colors.ORANGE,
            16: ft.Colors.DEEP_ORANGE,
            18: ft.Colors.RED,
        }.get(movie.age_restriction, ft.Colors.GREY)

        super().__init__(
            ink=True,
            on_click=lambda _: self._on_click(self.movie.id),
            border_radius=12,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            padding=0,
            content=ft.Column(
                spacing=0,
                controls=[
                    ft.Container(
                        height=180,
                        bgcolor=ft.Colors.SURFACE_CONTAINER,
                        alignment=ft.alignment.Alignment(0, 0),
                        content=ft.Icon(ft.Icons.MOVIE_OUTLINED, size=60, color=ft.Colors.ON_SURFACE_VARIANT),
                    ),
                    ft.Container(
                        padding=12,
                        content=ft.Column(
                            spacing=6,
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text(
                                            movie.title,
                                            size=16,
                                            weight=ft.FontWeight.BOLD,
                                            max_lines=2,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                            expand=True,
                                        ),
                                        ft.Badge(
                                            label=ft.Text(f"{movie.age_restriction}+", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_PRIMARY),
                                            bgcolor=age_badge_color,
                                        ),
                                    ],
                                ),
                                ft.Row(
                                    spacing=12,
                                    controls=[
                                        ft.Row(
                                            spacing=4,
                                            controls=[
                                                ft.Icon(ft.Icons.CATEGORY, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                                ft.Text(movie.genre, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                                            ],
                                        ),
                                        ft.Row(
                                            spacing=4,
                                            controls=[
                                                ft.Icon(ft.Icons.TIMER_OUTLINED, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                                                ft.Text(f"{movie.duration} мин", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )
