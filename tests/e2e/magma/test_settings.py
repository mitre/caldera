"""
E2E tests for the Caldera Settings page (SettingsView.vue).

Settings displays Caldera's current main configuration and allows some
values to be updated via a code editor. It also lists active plugins.

Run with:
    pytest plugins/magma/tests/e2e/test_settings.py -v --browser chromium
"""

from playwright.sync_api import Page, expect


def test_settings_page_loads(auth_page: Page, base_url: str) -> None:
    """Navigating to /settings stays on /settings (no redirect to /login)."""
    auth_page.goto(base_url + '/settings')
    auth_page.wait_for_load_state('networkidle')
    assert '/login' not in auth_page.url, (
        f'Expected to stay on /settings but ended up at {auth_page.url}'
    )


def test_settings_config_api_returns_data(api_session, base_url: str) -> None:
    """GET /api/v2/config/main returns a dict with at least a 'port' key."""
    resp = api_session.get(f'{base_url}/api/v2/config/main')
    assert resp.status_code == 200
    config = resp.json()
    assert isinstance(config, dict)
    assert 'port' in config, f"'port' key missing from config: {list(config.keys())}"


def test_settings_displays_port_value(auth_page: Page, api_session, base_url: str) -> None:
    """The server port from the API config appears somewhere on the settings page."""
    resp = api_session.get(f'{base_url}/api/v2/config/main')
    port = str(resp.json().get('port', ''))
    assert port, "Could not determine port from config API"

    auth_page.goto(base_url + '/settings')
    auth_page.wait_for_load_state('networkidle')
    expect(auth_page.get_by_text(port, exact=False)).to_be_visible()


def test_settings_plugins_api_returns_list(api_session, base_url: str) -> None:
    """GET /api/v2/plugins returns a non-empty list of plugin objects."""
    resp = api_session.get(f'{base_url}/api/v2/plugins')
    assert resp.status_code == 200
    plugins = resp.json()
    assert isinstance(plugins, list)
    assert len(plugins) > 0, "Expected at least one plugin to be registered"


def test_settings_page_has_code_editor(auth_page: Page, base_url: str) -> None:
    """A code editor element is present on the settings page for config editing."""
    auth_page.goto(base_url + '/settings')
    auth_page.wait_for_load_state('networkidle')
    # CodeEditor component renders a prism-editor or textarea
    editor = auth_page.locator(
        '.prism-editor__textarea, textarea, .code-editor, [contenteditable="true"]'
    ).first
    expect(editor).to_be_visible()


def test_settings_api_key_not_in_page_source(auth_page: Page, api_session, base_url: str) -> None:
    """
    The raw api_key_red value from the config API should NOT appear verbatim
    in the rendered page — it must be masked or omitted in the UI.
    """
    config_resp = api_session.get(f'{base_url}/api/v2/config/main')
    api_key = config_resp.json().get('api_key_red', '')

    if not api_key or api_key.startswith('$argon2'):
        # Hashed key — already opaque, skip this check
        return

    auth_page.goto(base_url + '/settings')
    auth_page.wait_for_load_state('networkidle')
    page_text = auth_page.content()
    assert api_key not in page_text, (
        'Raw api_key_red value is visible in the settings page source — '
        'it should be masked or omitted for security.'
    )


def test_settings_navigation_links_visible(auth_page: Page, base_url: str) -> None:
    """Navigation links to other sections are present on the settings page."""
    auth_page.goto(base_url + '/settings')
    auth_page.wait_for_load_state('networkidle')
    # The sidebar navigation should link to core views
    for label in ('Agents', 'Operations', 'Abilities'):
        expect(auth_page.get_by_role('link', name=label, exact=False)).to_be_visible()
