# Hydra shell — TASK-1

## Status and reuse decision

Implemented on 2026-07-14 after Person identity and organization scope.

| Concern | Decision | Rationale |
|---|---|---|
| legacy HR platform page frame | **REUSE** `index.html`, navbar, sidebar, notifications and profile controls | The shell must not fork or rewrite working HRMS infrastructure. |
| Hydra page frame | **WRAP** with `hydra_shell/base.html` | Hydra receives one branded workspace inside the existing authenticated frame. |
| People and Organization templates | **EXTEND** through the shared base | Both modules keep their server-rendered views and now use one responsive shell. |
| Branding and module navigation | **NEW** scoped CSS and template tags | Hydra-specific presentation stays isolated from non-Hydra legacy HR platform pages. |
| Public training portal | **WRAP** with an HTTPS-only URL builder | The existing portal remains external and receives only public language plus `from=hydra`. |

## Implemented vertical slice

`hydra_shell` is a template/static-only Django app. It has no models and creates no migration. It provides:

- a Hydra wordmark and workspace header;
- permission-aware People and Organization navigation;
- one active-module marker with `aria-current="page"`;
- a skip link, keyboard focus styles, 44 px-class touch targets and reduced-motion handling;
- responsive cards, forms, details, tables and organization hierarchy styles shared by all current Hydra screens;
- an external `Training / Hydra` link with a visible external-site label and safe `noopener noreferrer external` attributes;
- mobile initialization that collapses the inherited legacy HR platform sidebar while preserving the existing menu button for reopening it.

The previous inline CSS in `hydra_people/base.html` moved to the shell's namespaced static stylesheet. The People base is now a compatibility shim over `hydra_shell/base.html`, so Organization is migrated without changing each individual template.

## Permissions and scope

Navigation visibility is not an authorization mechanism. People appears only with `hydra_people.view_person`; Organization appears only with `hydra_coordination.view_location`. Their existing decorated views, scoped selectors and write services remain the server-side enforcement boundary. The public training link contains no Person, Employee, company, location, team, token or session data.

## Public portal configuration

`HYDRA_PORTAL_URL` defaults to the audited GitHub Pages project root and may be overridden through the environment. Django's security checks reject relative or non-HTTPS values as `hydra_shell.E001`.

The generated URL discards any configured query and fragment, maps Django `uk` to the portal's `ua`, falls back to `ru` for unsupported languages and emits only:

```text
?lang=<public-language>&from=hydra
```

Per-location training configuration remains a later portal-integration task; this shell exposes only the stable public start portal.

## Automated verification

The focused suite contains 32 tests and covers:

- existing Person and organization business behavior;
- permission-without-scope and cross-team denial;
- People/Organization navigation visibility and active state;
- rendering the stylesheet and mobile initialization script;
- Ukrainian alias mapping and unsupported-language fallback;
- rejection of insecure/relative portal URLs;
- removal of identity/token query data from public links.

The final completion report records the full PostgreSQL test and diagnostic commands.

## Browser verification

Verified in the in-app browser against the local PostgreSQL-backed server:

- desktop People rendered at 1280 px with the branded shell, both authorized modules and only the scoped Person;
- at 390 × 844, the inherited sidebar collapsed, the document measured 390 px with no horizontal overflow, shell width was 386 px and navigation width was 361 px;
- People table rows became readable mobile cards and the active tab remained unique;
- Organization rendered without horizontal overflow, showed only Browser Location A and excluded Browser Location B;
- the inherited menu button reopened the 230 px legacy HR platform sidebar and closed it again successfully.

## Manual test steps

1. Start the PostgreSQL-backed application and sign in as a scoped user.
2. Open `/hydra/people/` and confirm the shell shows only modules allowed by Django permissions.
3. Follow Organization and confirm `aria-current`/active styling moves to that module.
4. Resize to 390 × 844 and confirm there is no horizontal scroll.
5. Open and close the inherited legacy HR platform sidebar with the navbar menu button.
6. Open `Training / Hydra` and confirm the external URL contains only `lang` and `from=hydra`.
7. Remove each view permission and confirm its link disappears while direct endpoints still enforce 403/404 as previously tested.

## Known limitations and next task

- Translation strings are ready for catalogs, but catalogs are not populated yet.
- Only implemented Hydra modules appear in the local module navigation; later apps must opt into the shell and add explicit permission-gated links.
- Per-location training URLs and content ownership remain outside this slice.
- The shell intentionally retains legacy HR platform's outer navbar/sidebar and does not rebrand unrelated HRMS pages.

Next: extend recruitment with the existing Candidate/Application boundary and current organization selectors.
