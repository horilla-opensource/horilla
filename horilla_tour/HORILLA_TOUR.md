# Horilla Tour & Getting Started Checklist

Functional and technical reference for Horilla’s onboarding UX:

1. **Product Tours** (`horilla_tour`) — guided, driver.js walkthroughs on any page
2. **Setup Checklist** — “Get started with Horilla HR” banner on the dashboard (8 setup steps)

These systems are complementary: the checklist drives first-time HR configuration; product tours teach UI features after (or during) setup.

---

## Part 1 — Product Tours (`horilla_tour`)

### Functional overview

| Capability | Behavior |
|---|---|
| Author tours in UI | Admins create/edit tours and ordered steps from **Settings → Product Tours** (no code deploy). |
| Page targeting | Tours match by Django URL name (exact) or path prefix. Blank = any page. |
| Audience | Everyone, Admins/Superusers, Reporting managers, or Employees (non-managers). |
| Trigger | `auto_once` — auto-start once per user, then available on demand; `manual` — Help launcher only. |
| Progress | Per-user status: `in_progress`, `completed`, `skipped` (replaces legacy `base.DriverViewed`). |
| Multi-tenant | Scoped by `company_id`; `company_id=None` = global tour for all tenants. |
| Help launcher | Header “Take a tour” opens a panel to Start / Replay tours for the current page. |
| Draft vs live | Unpublished tours never appear to end users. |

**Admin flow**

1. Open Settings → **Manage Tours**
2. Create a tour (title, slug, audience, page match, trigger, publish flag)
3. Open **Steps** → add ordered steps with CSS selector, title, description, popover side/align
4. Publish → users matching audience + page see auto-start or launcher entry

**End-user flow**

1. Authenticated page load injects `window.HORILLA_TOUR` and `tourController.js`
2. JS calls `GET /tour/api/active/?page=&path=`
3. Highest-priority unfinished `auto_once` tour starts via driver.js
4. On close/finish, JS posts status to `POST /tour/api/progress/`
5. User can reopen tours from the Help launcher anytime

---

### Technical architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Templates (footer_scripts.html)                            │
│    window.HORILLA_TOUR = { page, path, activeUrl, … }       │
│    + static/build/js/tourController.js                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ fetch
┌──────────────────────────▼──────────────────────────────────┐
│  JSON API                                                   │
│    GET  tour-active   → published tours + steps for page    │
│    POST tour-progress → upsert TourProgress                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  Models (HorillaModel + HorillaCompanyManager)              │
│    Tour → TourStep (ordered)                                │
│    TourProgress (unique tour + user)                        │
└─────────────────────────────────────────────────────────────┘
```

#### App registration

- Installed app: `horilla_tour` (`horilla/settings/base.py`)
- URLs: `path("", include("horilla_tour.urls"))` in `horilla/urls.py`
- Context processor: `horilla_tour.context_processors.pending_tours_flag`
  - Exposes `tour_launcher_enabled`, `tour_has_pending` for the header Help button
- Settings menu: `horilla_tour/sidebar.py` → “Product Tours / Manage Tours”
- Scripts: `horilla_theme/.../footer_scripts.html` (authenticated only)

#### Data model

**`Tour`**

| Field | Notes |
|---|---|
| `title`, `slug`, `description` | Display + stable key for seeds |
| `page_match` + `match_type` | `url_name` or `path_prefix` |
| `audience` | `all` / `admins` / `managers` / `employees` |
| `trigger` | `auto_once` / `manual` |
| `is_published`, `priority` | Draft gate; higher priority auto-starts first |
| `show_progress`, `allow_close` | driver.js options |
| `icon` | ion-icon name in launcher |
| `company_id` | FK; null = global |

**`TourStep`**

| Field | Notes |
|---|---|
| `tour`, `sequence` | Parent + order |
| `title`, `description` | Popover copy |
| `element_selector` | CSS selector; blank = centered message |
| `side`, `align` | Popover position (`top`/`bottom`/`left`/`right`/`over`) |
| `page_match` | Optional URL name for multi-page tours |

**`TourProgress`**

| Field | Notes |
|---|---|
| `tour`, `user` | Unique together |
| `status` | `in_progress` / `completed` / `skipped` |
| `last_step`, `completed_at` | Resume / audit |

#### Public API

| URL name | Path | Method | Purpose |
|---|---|---|---|
| `tour-active` | `/tour/api/active/` | GET | Tours for current page + user (auth required) |
| `tour-progress` | `/tour/api/progress/` | POST | `tour_id`, `status`, `last_step` |

**`tour_active` filtering**

1. `is_active` + `is_published`
2. Audience via `_audiences_for(user)` (superuser gets all; managers detected via `EmployeeWorkInformation.reporting_manager_id`)
3. Page match (`_tour_matches_page`)
4. Non-empty steps for current page
5. `auto_start = trigger == auto_once` and status not completed/skipped

#### Settings CRUD (permission-gated)

| URL name | View | Permission |
|---|---|---|
| `tour-section` | Settings page shell | `view_tour` |
| `tour-nav` / `tour-list` | HorillaNavView / HorillaListView | `view_tour` |
| `tour-create-form` / `tour-update-form` | HorillaFormView | `add_tour` / change via update |
| `tour-steps` / `tour-step-form` / `tour-step-delete` | HTMX panel | `view_tour` / `change_tour` |

Patterns: HorillaListView row actions, HTMX modals, generic delete.

#### Frontend (`tourController.js`)

- Depends on global **driver.js** (`window.driver.js.driver`)
- Reads `window.HORILLA_TOUR`
- Builds driver steps from API payload
- On destroy: posts `completed` if last step reached, else `skipped`
- Exposes launcher UI (`#horillaTourLauncher`) and `window.horillaTour` for Start/Replay
- Header button `#tourLauncherBtn` toggles the panel

#### Permissions

Django model perms on `horilla_tour.Tour`:

- `view_tour` — see settings + list
- `add_tour` / `change_tour` / `delete_tour` — CRUD

End users only need authentication for the JSON API.

---

## Part 2 — Setup Checklist (“Get started with Horilla HR”)

Dashboard onboarding banner that walks admins through foundational HR configuration. Not part of `horilla_tour`, but the primary “first run” tour of the product.

### Functional overview

**Copy & UX**

- Title: **Get started with Horilla HR**
- Subtitle: `N of 8 steps complete — finish setup to unlock your full HR system`
- Progress bar + step circles with connector lines
- Action card: **Next: {step}** + short description + **Set up now** CTA
- Dismiss (×) hides the banner for that user + company

**Eight steps**

| # | Key | Title | What “done” means | Destination URL name |
|---|---|---|---|---|
| 1 | `company` | Company | Any `Company` exists | `company-view` |
| 2 | `department` | Departments | Department for active company | `department-view` |
| 3 | `job_position` | Job Positions | JobPosition for company | `job-position-view` |
| 4 | `work_type` | Work Types | WorkType for company | `work-type-view` |
| 5 | `employee_type` | Employee Types | EmployeeType for company | `employee-type-view` |
| 6 | `shift` | Shifts | EmployeeShift for company | `employee-shift-view` |
| 7 | `mail_server` | Mail Server | Primary `DynamicEmailConfiguration` with host | `mail-server-conf` |
| 8 | `first_employee` | First Employee | Employee for company | `employee-view-new` |

Example next-step card:

> **Next: Company**
> Add your company profile — name, logo and timezone.
> [Set up now →]

**Visibility rules**

- Shown only to setup admins: superuser, staff, or users with `base.add_department` / `base.add_company`
- Hidden if user dismissed for the active company (`SetupChecklistDismissal`)
- Hidden when all 8 steps are complete
- DEBUG only: `?preview_checklist=1` forces the banner with all steps incomplete

---

### Technical architecture

```
main_dashboard_view
    └─ _get_setup_checklist_context(request)
           └─ templates/dashboard.html
                  └─ {% include "base/setup_checklist_banner.html" %}
                         └─ {% include "base/setup_checklist_step.html" %}
```

#### Key files

| Path | Role |
|---|---|
| `base/dashboard.py` | `_get_setup_checklist_context`, `dismiss_setup_checklist` |
| `base/models.py` | `SetupChecklistDismissal` |
| `base/urls.py` | dismiss route → `dashboard-dismiss-setup-checklist` |
| `base/templates/base/setup_checklist_banner.html` | Banner UI + CSS (`.hcl-*`) |
| `base/templates/base/setup_checklist_step.html` | One step circle + connectors |
| `templates/dashboard.html` | `{% if show_setup_checklist %}` include |

#### Context variables (when shown)

| Variable | Meaning |
|---|---|
| `show_setup_checklist` | Render banner |
| `setup_steps` | List of step dicts (`key`, `title`, `description`, `url`, `done`, line flags) |
| `setup_completed` / `setup_total` | Progress counts |
| `setup_progress_pct` | Bar width % |
| `setup_next_step` | First incomplete step (or `None`) |
| `setup_dismiss_url` | HTMX POST target |
| `setup_company_pk` | Active company scope |

#### Company scoping

`_resolve_checklist_company`:

1. Middleware selected company (not `"all"`)
2. Else first `Company` in DB
3. Else `None` (Company step still incomplete)

`_exists_for_company` mirrors `HorillaCompanyManager`: record counts if assigned to company **or** company FK/M2M is null (shared lookup data).

#### Dismiss endpoint

- `POST` → `dismiss_setup_checklist`
- Creates `SetupChecklistDismissal(user, company)`
- Returns empty HTML; banner uses `hx-target="#setup-checklist-banner"` + `hx-swap="outerHTML"`

#### UI / CSS notes

Banner classes (`hcl-banner`, `hcl-progress-*`, `hcl-circle-*`, `hcl-action`, …):

- Brand coral gradient (`#e54f38` / `#e8705e`)
- Dark-mode variants via `.dark`
- Step states: **done** (filled check), **active** (ring + shadow), **pending**
- Connector lines fill progressively when the previous step is done
- Accessible: `role="progressbar"`, `aria-current="step"`, i18n via `{% trans %}` / `{% blocktrans %}`

---

## How the two systems differ

| | Product Tour | Setup Checklist |
|---|---|---|
| App | `horilla_tour` | `base` (+ dashboard) |
| Purpose | Teach UI features | Complete HR foundation data |
| Rendering | driver.js overlays | Static banner on dashboard |
| Content source | DB tours/steps (admin-authored) | Hard-coded step list in Python |
| Progress store | `TourProgress` | Live DB existence checks + optional dismissal |
| Trigger | Page match + audience | Admin on dashboard until done/dismissed |

---

## Quick reference — important paths

```
horilla_tour/
  models.py              Tour, TourStep, TourProgress
  views.py               API + Settings CRUD
  urls.py                tour-active, tour-progress, settings routes
  context_processors.py  launcher flag
  sidebar.py             Settings menu
  templates/horilla_tour/

static/build/js/tourController.js

base/dashboard.py                    setup checklist context + dismiss
base/templates/base/setup_checklist_banner.html
base/templates/base/setup_checklist_step.html
horilla_theme/.../footer_scripts.html   HORILLA_TOUR bootstrap
horilla_theme/.../header.html           Take a tour button
```

---

## Developer tips

1. **New product tour** — prefer Settings UI; use a stable `slug` if seeding via data migration.
2. **Selectors** — use stable IDs/classes (`#notificationIcon`); avoid ephemeral HTMX markup.
3. **Multi-page tours** — set step-level `page_match` to the URL name for each step’s page.
4. **Test checklist UI** — with `DEBUG=True`, open dashboard with `?preview_checklist=1`.
5. **Never break pages** — `pending_tours_flag` swallows exceptions; tour progress posts are best-effort on the client.
6. **Permissions** — grant `horilla_tour.view_tour` (and change/add) only to admins who should author tours.
`)
