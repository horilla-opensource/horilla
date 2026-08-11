"""E2E (Playwright): menu do usuário do header em Português (Brasil) — feature 002, US1.

NOTA: `templates/navbar.html` (referenciado no spec/plan original desta feature
com as strings "My Profile"/"Company Information"/"Notifications"/"Employees"/
"Log out") não é incluído por nenhum template em uso — é código morto (nenhuma
view/template referencia esse arquivo). O menu do usuário realmente renderizado
vem de `horilla_theme/templates/base/navbar_components/profile_section.html`
(incluído via `horilla_theme/templates/horilla_theme/components/header.html`),
que já usa `{% trans %}` em todos os seus itens.

O menu é revelado via CSS puro (`:hover`/`:focus-within` em `.dropdown-wrapper
.dropdown-content`), não por um clique que alterna uma classe — por isso este
teste verifica o texto já presente no HTML renderizado pelo servidor
(`.dropdown-content`), sem precisar abrir o menu visualmente.
"""

ENGLISH_MENU_STRINGS = [
    "My Profile",
    "Change Username",
    "Change Password",
    "Logout",
]


def test_navbar_user_menu_is_translated_to_pt_br(pt_br_page):
    page = pt_br_page
    menu_text = page.locator(
        ".dropdown-wrapper:has(img.downarrow) .dropdown-content"
    ).text_content()

    for english_string in ENGLISH_MENU_STRINGS:
        assert english_string not in menu_text, (
            f'"{english_string}" ainda aparece em inglês no menu do usuário '
            "com Português (Brasil) selecionado"
        )
