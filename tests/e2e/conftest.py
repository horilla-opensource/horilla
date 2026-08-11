"""Fixtures compartilhadas para os testes E2E Playwright (feature 002)."""

import os

import pytest
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("HORILLA_E2E_BASE_URL", "http://127.0.0.1:8000")
PT_BR_USERNAME = os.environ.get("HORILLA_E2E_PT_BR_USERNAME", "e2e_ptbr")
PT_BR_PASSWORD = os.environ.get("HORILLA_E2E_PT_BR_PASSWORD", "e2e_ptbr_password")
EN_USERNAME = os.environ.get("HORILLA_E2E_EN_USERNAME", "e2e_en")
EN_PASSWORD = os.environ.get("HORILLA_E2E_EN_PASSWORD", "e2e_en_password")


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


def _login(browser, username, password, language):
    context = browser.new_context(base_url=BASE_URL)
    page = context.new_page()
    page.goto(f"{BASE_URL}/login/")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_selector("nav[aria-label]", timeout=15000)
    # Setar o idioma DEPOIS do login: o login() do Django cicla a chave da
    # sessão (proteção contra session fixation), o que descartaria a
    # preferência de idioma se ela fosse setada antes de autenticar.
    page.goto(f"{BASE_URL}/i18n/setlang/")
    csrftoken = next(
        (c["value"] for c in context.cookies() if c["name"] == "csrftoken"), None
    )
    page.request.post(
        f"{BASE_URL}/i18n/setlang/",
        form={"language": language, "next": "/", "csrfmiddlewaretoken": csrftoken},
        headers={"Referer": f"{BASE_URL}/i18n/setlang/"},
    )
    page.goto(f"{BASE_URL}/dashboard/")
    page.wait_for_selector("nav[aria-label]", timeout=15000)
    return page


@pytest.fixture
def pt_br_page(browser):
    """Página autenticada com o usuário de teste configurado em Português (Brasil)."""
    page = _login(browser, PT_BR_USERNAME, PT_BR_PASSWORD, "pt-br")
    yield page
    page.context.close()


@pytest.fixture
def en_page(browser):
    """Página autenticada com o usuário de teste configurado em Inglês (padrão)."""
    page = _login(browser, EN_USERNAME, EN_PASSWORD, "en")
    yield page
    page.context.close()
