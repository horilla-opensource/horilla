# Contributing Guidelines for Horilla

Thank you for considering contributing to Horilla! We welcome your input and appreciate the community effort to make this project even better.

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
- **Security vulnerabilities:** do **not** open a public issue — report via GitHub Private Vulnerability Reporting only, per [SECURITY.md](SECURITY.md).

## Community Guidelines

- Be respectful and considerate of others.
- Provide constructive feedback.
- Encourage a positive and inclusive community.

Thank you for your contributions to Horilla!
