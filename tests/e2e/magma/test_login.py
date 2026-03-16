"""
E2E tests for the Caldera login page (LoginView.vue).

These tests cover the unauthenticated login flow, credential validation,
page structure, and redirect behaviour for already-authenticated users.

Tests that exercise the login form itself (1–4) use the bare `page` fixture
so no auth cookies are present.  Test 5 uses `auth_page` to verify that an
already-authenticated session is bounced away from /login.

Run with:
    pytest plugins/magma/tests/e2e/test_login.py -v --browser chromium
"""

import pytest
from playwright.sync_api import expect, Page


# ---------------------------------------------------------------------------
# 1. Unauthenticated visit to / redirects to /login and page is well-formed
# ---------------------------------------------------------------------------

def test_login_page_loads(page: Page, caldera_server: str) -> None:
    """
    An unauthenticated GET to / should redirect to /login.
    The login page must contain a username input, a password input,
    and a 'Log In' submit button.
    """
    # Navigate to the root; the Vue router should redirect to /login
    page.goto(caldera_server + '/')
    page.wait_for_load_state('networkidle')

    # Confirm we landed on the login route
    assert '/login' in page.url, (
        f"Expected redirect to /login but current URL is {page.url}"
    )

    # Username field
    username_input = page.locator('input[type="text"][placeholder="username"]')
    expect(username_input).to_be_visible()

    # Password field
    password_input = page.locator('input[type="password"][placeholder="password"]')
    expect(password_input).to_be_visible()

    # Submit button
    login_button = page.locator('button', has_text='Log In')
    expect(login_button).to_be_visible()


# ---------------------------------------------------------------------------
# 2. Valid credentials log in and redirect away from /login
# ---------------------------------------------------------------------------

def test_login_with_valid_credentials(page: Page, caldera_server: str) -> None:
    """
    Submitting correct credentials (admin/admin) should navigate the user
    away from /login (typically to /).  No error text should be visible.
    """
    page.goto(caldera_server + '/login')
    page.wait_for_load_state('networkidle')

    # Fill the form
    page.locator('input[type="text"][placeholder="username"]').fill('admin')
    page.locator('input[type="password"][placeholder="password"]').fill('admin')

    # Click the login button and wait for navigation to settle
    page.locator('button', has_text='Log In').click()
    page.wait_for_load_state('networkidle')

    # After a successful login the URL must no longer be /login
    assert '/login' not in page.url, (
        f"Login appeared to fail — still on {page.url}"
    )

    # The error container should be empty / invisible
    error_paragraph = page.locator('.has-text-danger p')
    # Either the element is absent from the DOM, or its text content is blank
    if error_paragraph.count() > 0:
        assert error_paragraph.inner_text().strip() == '', (
            f"Unexpected login error shown: '{error_paragraph.inner_text()}'"
        )


# ---------------------------------------------------------------------------
# 3. Invalid credentials stay on /login and show an error message
# ---------------------------------------------------------------------------

def test_login_with_invalid_credentials(page: Page, caldera_server: str) -> None:
    """
    Submitting a wrong password should keep the user on /login and render
    a non-empty error message inside `.has-text-danger p`.
    """
    page.goto(caldera_server + '/login')
    page.wait_for_load_state('networkidle')

    # Fill with a bad password
    page.locator('input[type="text"][placeholder="username"]').fill('admin')
    page.locator('input[type="password"][placeholder="password"]').fill('wrongpassword')
    page.locator('button', has_text='Log In').click()
    page.wait_for_load_state('networkidle')

    # Must still be on the login page
    assert '/login' in page.url, (
        f"Expected to remain on /login after bad credentials, but URL is {page.url}"
    )

    # Error paragraph must be visible and non-empty
    error_paragraph = page.locator('.has-text-danger p')
    expect(error_paragraph).to_be_visible()
    assert error_paragraph.inner_text().strip() != '', (
        "Expected a non-empty error message after failed login, but got empty text"
    )


# ---------------------------------------------------------------------------
# 4. Login page displays the Caldera logo
# ---------------------------------------------------------------------------

def test_login_page_has_caldera_logo(page: Page, caldera_server: str) -> None:
    """
    The login page should render an <img> with alt="Caldera Logo".
    """
    page.goto(caldera_server + '/login')
    page.wait_for_load_state('networkidle')

    logo = page.locator('img[alt="Caldera Logo"]')
    expect(logo).to_be_visible()


# ---------------------------------------------------------------------------
# 5. Already-authenticated user visiting /login is redirected away
# ---------------------------------------------------------------------------

def test_authenticated_user_redirected_from_login(
    auth_page: Page, caldera_server: str
) -> None:
    """
    When a browser session already holds valid auth cookies, navigating to
    /login should immediately redirect to / (or another authenticated route)
    rather than rendering the login form.
    """
    auth_page.goto(caldera_server + '/login')
    auth_page.wait_for_load_state('networkidle')

    # The Vue router guards should have pushed the user away from /login
    assert '/login' not in auth_page.url, (
        f"Authenticated user was not redirected from /login; current URL: {auth_page.url}"
    )
