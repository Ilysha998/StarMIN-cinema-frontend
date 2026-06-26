import flet as ft
from api.client import ApiClient
from state.app_state import AppState
from config import config

from views.login_view import LoginView
from views.billboard_view import BillboardView
from views.films_view import FilmsView
from views.movie_detail_view import MovieDetailView
from views.session_detail_view import SessionDetailView
from views.tickets_view import TicketsView
from views.profile_view import ProfileView
from views.admin.admin_movies import AdminMoviesView
from views.admin.admin_sessions import AdminSessionsView
from views.admin.admin_users import AdminUsersView
from api.halls import HallsApi
from views.admin.admin_stats import AdminStatsView

from widgets.adaptive_nav import build_adaptive_nav, NAV_BILLBOARD, NAV_FILMS, NAV_TICKETS, NAV_PROFILE, NAV_ADMIN


def main(page: ft.Page):
    page.title = "StarMIN Cinema"
    page.window.width = 1100
    page.window.height = 700
    page.window.min_width = 400
    page.window.min_height = 500
    page.padding = 0

    api_client = ApiClient(base_url=config.backend_url, timeout=config.request_timeout)
    app_state = AppState()
    sp = ft.SharedPreferences()

    _nav_component = None
    _nav_position = ""
    _current_nav_index = NAV_BILLBOARD
    _view_stack: list = []
    _browsing = False
    _layout_ready = False
    _current_view = None
    _halls_map: dict = {}

    def _setup_themes():
        page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=ft.Colors.INDIGO,
                on_primary=ft.Colors.WHITE,
                primary_container=ft.Colors.INDIGO_50,
                on_primary_container=ft.Colors.INDIGO_900,
                secondary=ft.Colors.AMBER,
                surface=ft.Colors.GREY_50,
                on_surface=ft.Colors.GREY_900,
            ),
        )
        page.dark_theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=ft.Colors.INDIGO_300,
                on_primary=ft.Colors.BLACK,
                primary_container=ft.Colors.INDIGO_700,
                on_primary_container=ft.Colors.INDIGO_100,
                secondary=ft.Colors.AMBER_200,
                surface=ft.Colors.GREY_900,
                on_surface=ft.Colors.GREY_50,
            ),
        )

    _setup_themes()
    page.theme_mode = ft.ThemeMode.SYSTEM

    _content_area = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)

    async def _restore_session():
        nonlocal _browsing, _layout_ready
        saved_theme = await sp.get("starmin_theme")
        if saved_theme == "light":
            page.theme_mode = ft.ThemeMode.LIGHT
        elif saved_theme == "dark":
            page.theme_mode = ft.ThemeMode.DARK
        else:
            page.theme_mode = ft.ThemeMode.SYSTEM

        saved_token = await sp.get("starmin_token")
        saved_url = await sp.get("starmin_url")
        if saved_url:
            api_client.set_base_url(saved_url)
        if saved_token:
            api_client.token = saved_token
            try:
                from api.auth import AuthApi
                user = AuthApi(api_client).get_me()
                app_state.set_auth(saved_token, user)
            except Exception:
                api_client.token = None
                await sp.remove("starmin_token")

        _browsing = not app_state.is_logged_in
        _layout_ready = True
        try:
            halls = HallsApi(api_client).get_all()
            _halls_map = {h.id: h.name for h in halls}
        except Exception:
            _halls_map = {}
        _build_nav()
        _navigate_to(NAV_BILLBOARD)
        page.update()

    def _build_nav():
        nonlocal _nav_component, _nav_position
        _nav_component, _nav_position = build_adaptive_nav(
            page,
            on_change=_on_nav_change,
            selected_index=_current_nav_index,
            show_admin=app_state.is_admin,
        )
        _rebuild_layout()

    def _rebuild_layout():
        page.controls.clear()
        page.bottom_appbar = None

        if not app_state.is_logged_in and not _browsing:
            page.add(
                ft.Container(
                    expand=True,
                    alignment=ft.alignment.Alignment(0, 0),
                    content=LoginView(
                        api_client, app_state,
                        on_login=_on_login_success,
                        on_skip=_on_skip_login,
                        on_url_change=_on_url_change,
                    ),
                )
            )
        else:
            if _nav_position == "side":
                page.add(ft.Row(expand=True, controls=[
                    _nav_component,
                    ft.VerticalDivider(width=1),
                    _content_area,
                ]))
            else:
                page.add(ft.Column(expand=True, controls=[_content_area]))
                page.bottom_appbar = _nav_component
        page.update()

    async def _on_login_success():
        nonlocal _browsing, _current_nav_index
        _browsing = False
        await sp.set("starmin_token", app_state.token)
        _view_stack.clear()
        _current_nav_index = NAV_BILLBOARD
        _build_nav()
        _navigate_to(NAV_BILLBOARD)

    def _on_skip_login():
        nonlocal _browsing, _current_nav_index
        _browsing = True
        _view_stack.clear()
        _current_nav_index = NAV_BILLBOARD
        _build_nav()
        _navigate_to(NAV_BILLBOARD)

    async def _on_logout():
        nonlocal _browsing
        app_state.clear_auth()
        api_client.token = None
        _browsing = False
        await sp.remove("starmin_token")
        _view_stack.clear()
        _rebuild_layout()

    async def _on_theme_change(is_dark: bool):
        mode = ft.ThemeMode.DARK if is_dark else ft.ThemeMode.LIGHT
        page.theme_mode = mode
        await sp.set("starmin_theme", "dark" if is_dark else "light")
        page.update()

    async def _on_url_change(url: str):
        await sp.set("starmin_url", url)

    def _on_nav_change(index: int):
        nonlocal _current_nav_index
        if _current_nav_index == index and not _view_stack:
            return
        _view_stack.clear()
        _current_nav_index = index
        _navigate_to(index)

    def _show_login_in_content():
        _content_area.controls.clear()
        _content_area.controls.append(
            ft.Container(
                expand=True,
                alignment=ft.alignment.Alignment(0, 0),
                content=LoginView(
                    api_client, app_state,
                    on_login=_on_login_success,
                    on_skip=_on_skip_login,
                    on_url_change=_on_url_change,
                ),
            )
        )
        _update_nav_selection()
        page.update()

    def _navigate_to(index: int):
        nonlocal _current_nav_index, _current_view
        if _browsing and index in (NAV_TICKETS, NAV_PROFILE, NAV_ADMIN):
            _current_nav_index = index
            _update_nav_selection()
            _show_login_in_content()
            return

        _content_area.controls.clear()
        view = None

        if index == NAV_BILLBOARD:
            view = BillboardView(api_client, app_state, on_session_click=_on_session_click, on_movie_click=_on_movie_click, halls_map=_halls_map)
        elif index == NAV_FILMS:
            view = FilmsView(api_client, app_state, on_movie_click=_on_movie_click)
        elif index == NAV_TICKETS:
            view = TicketsView(api_client, app_state)
        elif index == NAV_PROFILE:
            view = ProfileView(api_client, app_state, on_logout=_on_logout, on_theme_change=_on_theme_change, on_url_change=_on_url_change)
        elif index == NAV_ADMIN:
            view = _build_admin_view()

        if view:
            _content_area.controls.append(view)
            _current_view = view
        _update_nav_selection()
        page.update()

    def _build_admin_view():
        admin_tabs = ft.Tabs(
            content=ft.Column([
                ft.Tab(icon=ft.Icons.MOVIE_FILTER),
                ft.Container(content=AdminMoviesView(api_client, app_state), expand=True, padding=8),
                ft.Tab(icon=ft.Icons.CALENDAR_MONTH),
                ft.Container(content=AdminSessionsView(api_client, app_state), expand=True, padding=8),
                ft.Tab(icon=ft.Icons.PEOPLE),
                ft.Container(content=AdminUsersView(api_client, app_state), expand=True, padding=8),
                ft.Tab(icon=ft.Icons.BAR_CHART),
                ft.Container(content=AdminStatsView(api_client, app_state), expand=True, padding=8),
            ]),
            length=4,
            expand=True,
        )
        return ft.Column([admin_tabs], expand=True)

    def _push_view(view):
        nonlocal _current_nav_index, _current_view
        _view_stack.append(_current_nav_index)
        _content_area.controls.clear()
        _content_area.controls.append(view)
        _current_view = view
        page.update()

    def _pop_view():
        nonlocal _current_nav_index
        if _view_stack:
            prev_index = _view_stack.pop()
            _current_nav_index = prev_index
            _navigate_to(prev_index)

    def _on_session_click(session_id: int):
        _push_view(SessionDetailView(
            api_client, app_state, session_id,
            halls_map=_halls_map,
            on_back=_pop_view,
            on_ticket_bought=lambda: None,
        ))

    def _on_movie_click(movie_id: int):
        _push_view(MovieDetailView(
            api_client, app_state, movie_id,
            on_session_click=_on_session_click,
            on_back=_pop_view,
            halls_map=_halls_map,
        ))

    def _update_nav_selection():
        if _nav_component:
            _nav_component.selected_index = _current_nav_index
            if hasattr(_nav_component, "update"):
                _nav_component.update()

    def _on_resize(e):
        if _layout_ready:
            _build_nav()
            if _current_view and hasattr(_current_view, 'on_page_resize'):
                _current_view.on_page_resize()

    page.on_resize = _on_resize
    page.run_task(_restore_session)


ft.run(main)
