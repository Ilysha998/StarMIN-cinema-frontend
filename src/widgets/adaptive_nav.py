import flet as ft
from typing import Callable


NAV_BILLBOARD = 0
NAV_FILMS = 1
NAV_TICKETS = 2
NAV_PROFILE = 3
NAV_ADMIN = 4

_ICONS = [
    (ft.Icons.ACCESS_TIME, "Афиша"),
    (ft.Icons.LOCAL_MOVIES, "Фильмы"),
    (ft.Icons.CONFIRMATION_NUMBER, "Билеты"),
    (ft.Icons.PERSON, "Профиль"),
    (ft.Icons.ADMIN_PANEL_SETTINGS, "Админ"),
]


def build_adaptive_nav(
    page: ft.Page,
    on_change: Callable[[int], None],
    selected_index: int = 0,
    show_admin: bool = False,
) -> tuple:
    is_mobile = page.width < 800
    count = 5 if show_admin else 4
    sel = min(selected_index, count - 1)

    if is_mobile:
        destinations = [
            ft.NavigationBarDestination(icon=_ICONS[i][0], label=_ICONS[i][1])
            for i in range(count)
        ]
        bar = ft.NavigationBar(
            destinations=destinations,
            selected_index=sel,
            on_change=lambda e: on_change(e.control.selected_index),
        )
        return bar, "bottom"
    else:
        rail_destinations = [
            ft.NavigationRailDestination(icon=_ICONS[i][0], label=_ICONS[i][1])
            for i in range(count)
        ]
        rail = ft.NavigationRail(
            destinations=rail_destinations,
            selected_index=sel,
            on_change=lambda e: on_change(e.control.selected_index),
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=80,
            min_extended_width=200,
            extended=True,
        )
        return rail, "side"
