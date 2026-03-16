"""
Pytest configuration for Playwright E2E UI tests.

Each test session finds a free TCP port, writes a temporary conf/local.yml
(so multiple VENVs / CI jobs can run simultaneously without port conflicts),
starts Caldera on that port, waits until healthy, provides an authenticated
Playwright page, then tears everything down.

Prerequisites (installed by the `ui` tox environment):
    pip install playwright pytest-playwright requests
    playwright install chromium

Run:
    pytest plugins/magma/tests/e2e -v --browser chromium

Environment variables:
    CALDERA_PORT     Force a specific port (default: auto-detect a free port)
    CALDERA_USER     Username to log in as   (default: admin)
    CALDERA_PASS     Password                (default: admin)
    CALDERA_EXTERNAL Set to '1' to skip server startup and use CALDERA_URL
    CALDERA_URL      Base URL when CALDERA_EXTERNAL=1
    CALDERA_STARTUP_TIMEOUT  Seconds to wait for server (default: 90)
"""

import os
import shutil
import socket
import subprocess
import tempfile
import time

import pytest
import requests
import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(__file__)
CALDERA_ROOT = os.path.normpath(os.path.join(_HERE, '..', '..', '..', '..', '..'))
CONF_DIR = os.path.join(CALDERA_ROOT, 'conf')
DEFAULT_YML = os.path.join(CONF_DIR, 'default.yml')
LOCAL_YML = os.path.join(CONF_DIR, 'local.yml')

CALDERA_USER = os.environ.get('CALDERA_USER', 'admin')
CALDERA_PASS = os.environ.get('CALDERA_PASS', 'admin')
STARTUP_TIMEOUT = int(os.environ.get('CALDERA_STARTUP_TIMEOUT', '90'))


# ---------------------------------------------------------------------------
# Port helpers
# ---------------------------------------------------------------------------

def _find_free_port() -> int:
    """Bind to port 0 to let the OS assign a free ephemeral port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def _port_in_use(port: int) -> bool:
    """Return True if something is already listening on *port*."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1', port)) == 0


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _write_test_local_yml(port: int) -> None:
    """
    Write conf/local.yml based on conf/default.yml but with:
      - port overridden to *port*
      - host set to 127.0.0.1 (test-only, no external exposure)

    If conf/local.yml already exists it is backed up first so the original
    is restored in teardown.
    """
    with open(DEFAULT_YML, 'r', encoding='utf-8') as fh:
        config = yaml.safe_load(fh)

    config['port'] = port
    config['host'] = '127.0.0.1'

    with open(LOCAL_YML, 'w', encoding='utf-8') as fh:
        yaml.safe_dump(config, fh, default_flow_style=False)


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session')
def caldera_server():
    """
    Start Caldera on a free port using conf/local.yml, wait until healthy,
    yield the base URL, then terminate and clean up.

    Set CALDERA_EXTERNAL=1 to skip startup and connect to an already-running
    instance at CALDERA_URL instead.
    """
    if os.environ.get('CALDERA_EXTERNAL') == '1':
        yield os.environ.get('CALDERA_URL', 'http://localhost:8888')
        return

    # Choose port — env var overrides auto-detection
    port = int(os.environ.get('CALDERA_PORT', _find_free_port()))
    base_url = f'http://127.0.0.1:{port}'

    # Safety: refuse to start if something is already on this port.
    # Caldera loads all state into memory; writing conf/local.yml while a
    # running instance holds config in memory would be silently ignored and
    # could leave the config file in an inconsistent state.
    if _port_in_use(port):
        pytest.fail(
            f'Port {port} is already in use. '
            'Stop any running Caldera instance before running UI tests, '
            'or set CALDERA_PORT to a free port.'
        )

    # Back up existing local.yml if present
    local_yml_backup = None
    if os.path.exists(LOCAL_YML):
        local_yml_backup = LOCAL_YML + '.e2e_backup'
        shutil.copy2(LOCAL_YML, local_yml_backup)

    _write_test_local_yml(port)

    env = os.environ.copy()
    env['PYTHONPATH'] = CALDERA_ROOT

    proc = subprocess.Popen(
        # -E local → uses conf/local.yml we just wrote
        # -l ERROR  → suppress startup noise in test output
        ['python', 'server.py', '-E', 'local', '-l', 'ERROR'],
        cwd=CALDERA_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    health_url = f'{base_url}/api/v2/health'
    deadline = time.time() + STARTUP_TIMEOUT
    ready = False
    while time.time() < deadline:
        try:
            r = requests.get(health_url, timeout=2)
            if r.status_code == 200:
                ready = True
                break
        except requests.RequestException:
            pass
        time.sleep(1)

    if not ready:
        proc.terminate()
        # Restore backup before failing
        if local_yml_backup:
            shutil.move(local_yml_backup, LOCAL_YML)
        else:
            os.remove(LOCAL_YML)
        pytest.fail(
            f'Caldera did not become healthy within {STARTUP_TIMEOUT}s '
            f'(checked {health_url}). '
            f'Port {port} was selected.'
        )

    yield base_url

    # Teardown
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()

    if local_yml_backup:
        shutil.move(local_yml_backup, LOCAL_YML)
    elif os.path.exists(LOCAL_YML):
        os.remove(LOCAL_YML)


# ---------------------------------------------------------------------------
# API session (requests)
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session')
def api_session(caldera_server):
    """
    Authenticated requests.Session for direct API calls in tests.
    Used to set up / verify data independently of the browser.
    """
    session = requests.Session()
    resp = session.post(
        f'{caldera_server}/enter',
        data={'username': CALDERA_USER, 'password': CALDERA_PASS},
        allow_redirects=False,
    )
    assert resp.status_code in (200, 302), (
        f'Login failed: HTTP {resp.status_code}. '
        f'Verify CALDERA_USER/CALDERA_PASS match conf/local.yml credentials.'
    )
    return session


@pytest.fixture(scope='session')
def base_url(caldera_server):
    """Base URL of the running Caldera instance (e.g. http://127.0.0.1:54321)."""
    return caldera_server


# ---------------------------------------------------------------------------
# Playwright fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_page(page, caldera_server, api_session):
    """
    Playwright ``page`` pre-loaded with authentication cookies.

    Copies the requests.Session cookies into the Playwright browser context
    so tests start already logged in without going through the login form.
    The page is NOT yet navigated — tests must call ``page.goto(...)`` first.
    """
    pw_cookies = [
        {
            'name': c.name,
            'value': c.value,
            'domain': '127.0.0.1',
            'path': '/',
            'httpOnly': False,
            'secure': False,
        }
        for c in api_session.cookies
    ]
    if pw_cookies:
        page.context.add_cookies(pw_cookies)
    yield page
