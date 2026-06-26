import flet as ft
from models.movie import Movie
from models.session import Session
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional


AGE_COLORS = {
    0: ft.Colors.GREEN, 6: ft.Colors.BLUE, 12: ft.Colors.ORANGE,
    16: ft.Colors.DEEP_ORANGE, 18: ft.Colors.RED,
}
HALL_COLORS: Dict[int, str] = {}
HALL_NAMES: Dict[int, str] = {}


class _TimeChip(ft.Container):
    def __init__(self, session: Session, movie: Movie, halls_map: Optional[Dict[int, str]] = None, on_click: Callable[[int], None] | None = None):
        now = datetime.now()
        ended = session.datetime + timedelta(minutes=movie.duration) < now
        time_str = session.datetime.strftime("%H:%M")
        hall_name = (halls_map or HALL_NAMES).get(session.hall_id, f"Зал {session.hall_id}")
        hall_c = HALL_COLORS.get(session.hall_id, ft.Colors.GREY)

        if ended:
            super().__init__(
                border_radius=6,
                bgcolor=ft.Colors.SURFACE_CONTAINER,
                alignment=ft.alignment.Alignment(0, 0),
                content=ft.Text(f"{time_str}", size=10, color=ft.Colors.ON_SURFACE_VARIANT, strikethrough=True),
            )
            return

        super().__init__(
            border_radius=6,
            bgcolor=hall_c,
            ink=True,
            alignment=ft.alignment.Alignment(0, 0),
            content=ft.Text(f"{time_str} {int(session.price)}₽", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_PRIMARY),
        )
        if on_click:
            sid = session.id
            self.on_click = lambda _, sid=sid: on_click(sid)


class BillboardTile(ft.Container):
    def __init__(self, movie: Movie, sessions: list[Session], on_session_click: Callable[[int], None], on_movie_click: Callable[[int], None], halls_map: Optional[Dict[int, str]] = None, width: int = 200):
        self.movie = movie
        self._on_session_click = on_session_click
        self._on_movie_click = on_movie_click

        today_sessions = [s for s in sessions if s.datetime.date() == datetime.now().date()]
        today_sessions.sort(key=lambda s: s.datetime)
        active = [s for s in today_sessions if s.datetime > datetime.now()]

        age_c = AGE_COLORS.get(movie.age_restriction, ft.Colors.GREY)

        cols = 3 if width >= 200 else 2
        time_grid = ft.Column(spacing=4)
        for i in range(0, len(active), cols):
            row = ft.Row(spacing=4, controls=[
                _TimeChip(active[j], movie, halls_map, on_session_click)
                for j in range(i, min(i + cols, len(active)))
            ])
            time_grid.controls.append(row)

        if not active:
            time_grid.controls.append(
                ft.Text("Нет сеансов", size=10, color=ft.Colors.ON_SURFACE_VARIANT)
            )

        age_badge = ft.Container(
            padding=ft.padding.Padding(4, 6, 4, 6),
            border_radius=6,
            bgcolor=age_c,
            content=ft.Text(f"{movie.age_restriction}+", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        )

        poster = ft.Container(
            height=int(width * 0.9),
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            alignment=ft.alignment.Alignment(-1, -1),
            padding=8,
            content=age_badge,
        )
        if movie.poster_url:
            poster.image = ft.DecorationImage(src=movie.poster_url, fit=ft.BoxFit.COVER)

        info = ft.Container(
            padding=8,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            content=ft.Column(
                spacing=2,
                controls=[
                    ft.Text(movie.title, size=14, weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"{movie.genre} · {movie.duration} мин", size=11, color=ft.Colors.ON_SURFACE_VARIANT, max_lines=1),
                    ft.Divider(height=4, color=ft.Colors.TRANSPARENT),
                    time_grid,
                ],
            ),
        )

        super().__init__(
            width=width,
            border_radius=12,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            ink=True,
            on_click=lambda _: self._on_movie_click(self.movie.id),
            content=ft.Column(
                spacing=0,
                controls=[poster, info],
            ),
        )
