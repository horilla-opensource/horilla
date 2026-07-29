# Contributing Guidelines for Horilla

Thank you for considering contributing to Horilla! We welcome your input and appreciate the community effort to make this project even better.

## Branches

- **`dev/v2.0`** — the active integration branch. Always clone this and always open PRs against this — never against `2.0` directly.
- **`2.0`** — the repository’s default branch: a periodic public snapshot for running/deploying, not where day-to-day development happens. GitHub pre-selects this as the PR base, so change it to `dev/v2.0` before submitting.
- **`1.0`/`master`** — v1, now deprioritized. See "Contributing to v1" below and [Discussion #1127](https://github.com/horilla/horilla-hr/discussions/1127) for full background.

## How to Contribute

1. **Fork the Repository**
   - Fork [horilla/horilla-hr](https://github.com/horilla/horilla-hr) on GitHub.

2. **Clone the Repository**

     ```bash
     git clone -b dev/v2.0 https://github.com/YOUR_USERNAME/horilla-hr.git
     cd horilla-hr
     git remote add upstream https://github.com/horilla/horilla-hr.git
     ```

3. **Create a Branch**

     ```bash
     git checkout -b feature-or-bugfix-branch
     ```

4. **Set Up Locally**

     ```bash
     python3 -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt
     pip install pre-commit
     pre-commit install
     # Optional Docker stack:
     make dev
     ```

5. **Make Changes**
   - Follow Horilla coding conventions (extend `HorillaModel`, use Horilla decorators, HTMX patterns).
   - Run formatters via pre-commit (Black + isort).

6. **Commit Changes**

     ```bash
     git commit -m "[ADD] APP: clear description of why"
     ```

     Allowed tags: `[ADD]`, `[FIX]`, `[UPDT]`, `[REMOVE]` (and existing `[FEAT]` where used).

7. **Push and Open a Pull Request**
   - Target branch: **`dev/v2.0`**
   - GitHub defaults your PR’s base branch to `2.0` — manually change it to `dev/v2.0` before submitting.
   - Provide a clear title/description and link related issues
   - CI should stay green: **Docker CI** + **Quality**

## Code Style and Guidelines

- Follow [PEP 8](https://pep8.org/); format with Black; sort imports with isort (`--profile black`).
- Keep changes focused; prefer small PRs for reviewability.
- Never commit secrets: `.env`, API keys, TLS keys, database dumps, or local SQLite files.
- Use `.env.dist` as the public template (`cp .env.dist .env`); keep real `.env` files local only.

## CI Expectations

| Workflow | What it checks |
|----------|----------------|
| `Docker CI` | Image build, migrate, collectstatic, `/health/`, `/ready/` |
| `Quality` | Black/isort on `horilla/settings` + `horilla/urls.py`, `manage.py check`, production settings gate |

## Issues

- Bugs and features: open a public GitHub issue with reproduction steps.
- **Security vulnerabilities:** do **not** open a public issue — use [GitHub Private Vulnerability Reporting](https://github.com/horilla/horilla-hr/security/advisories/new), not email. See [SECURITY.md](SECURITY.md) for full details.

### Contributing to v1 (1.0/master)

v1 is now deprioritized: fixes are considered case-by-case at maintainer discretion, with no guaranteed timeline and no new features backported. If you'd like to contribute a v1 fix, please open an issue first to confirm interest before submitting a PR.

## Community Guidelines

- Be respectful and considerate of others.
- Provide constructive feedback.
- Encourage a positive and inclusive community.

Thank you for your contributions to Horilla!
