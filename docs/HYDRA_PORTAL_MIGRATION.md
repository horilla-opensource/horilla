# Current Hydra portal migration strategy

## Audited snapshot

- Repository: `OleksandrKiris/citronex-hydra-project`
- Branch: `main`
- Commit: `2262497c6c53281b3bd55bee5b9eebc03064b582`
- Commit date: 2026-07-14

## Current role

The portal is a static, public, mobile-first start page hosted independently from Horilla. Its purpose is one stable link that helps a worker choose arrival guidance or a location-specific training site. It does not contain authenticated worker records and does not duplicate the training sites.

This portal must remain operational during the Hydra MVP.

## Current behavior

### Languages

The interface and intro are available in nine language codes:

| Portal code | Language | HTML `lang` behavior | Local intro audio |
|---|---|---|---|
| `pl` | Polish | `pl` | `intro-pl.mp3` |
| `ru` | Russian | `ru` | `intro-ru.mp3` |
| `ua` | Ukrainian | normalized to `uk` | `intro-ua.mp3` |
| `en` | English | `en` | `intro-en.mp3` |
| `az` | Azerbaijani | `az` | `intro-az.mp3` |
| `es` | Spanish | `es` | `intro-es.mp3` |
| `fil` | Filipino | `fil` | `intro-fil.mp3` |
| `id` | Indonesian | `id` | `intro-id.mp3` |
| `ne` | Nepali | `ne` | `intro-ne.mp3` |

Language selection order:

1. supported `?lang=` query parameter;
2. `localStorage.hydraLang`;
3. Russian as the default.

Changing language updates translated text, accessibility labels, the HTML language and every training link. Location training URLs receive `lang=<selected>` and `from=hydra`. The intro modal opens on first use, can play local language audio and records its seen state in local storage.

The repository includes a native-speaker review checklist for Azerbaijani, Filipino, Indonesian and Nepali. Technical completeness is not equivalent to linguistic approval; that review remains required.

### Public destinations

| Purpose/location | Stable destination |
|---|---|
| Arrival to work | `https://oleksandrkiris.github.io/przyjazd-do-pracy/?v=share-check-2&lang=ru` |
| Siechnice | `https://oleksandrkiris.github.io/citronex-siechnice-szkolenie/` |
| Ryczywół | `https://oleksandrkiris.github.io/citronex-ryczywol-szkolenie/` |
| Zgorzelec / Bogatynia | `https://oleksandrkiris.github.io/citronex-zgorzelec-bogatynia-szkolenie/` |

These destinations are external public sites from Hydra's perspective. The MVP must not copy or rewrite their content.

## PWA and offline behavior

`manifest.webmanifest` defines a standalone app, relative start/scope, white background, red theme and one 512×512 maskable-capable icon.

`sw.js`:

- precaches the start page, manifest and logo;
- removes older Hydra cache versions on activation;
- uses network-first behavior with cache fallback for same-origin GET requests;
- treats intro audio as network-first with cache fallback;
- falls back to `index.html` when a same-origin request is offline;
- ignores cross-origin training requests.

The service worker must remain confined to the public portal. It must never be copied unchanged onto authenticated Hydra pages because its fallback/cache policy could store private responses.

## Public/private boundary

### Keep public

- language selection and intro;
- general arrival directions;
- public maps and directions;
- public contact information approved for workers;
- basic arrival and location training instructions;
- stable links to external training sites.

### Require authentication in future Hydra

- assigned Person/employee/location/team information;
- onboarding assignments and completion;
- personalized arrival/housing/legalization status;
- tests, confirmations and acknowledgements;
- internal contacts or operational notes;
- documents and personal data.

## MVP integration

The Hydra shell implements the stable root link through the HTTPS-only `HYDRA_PORTAL_URL` setting. It maps the current public language, adds `from=hydra`, labels the destination as external and transmits no authenticated identifier.

Task 043 adds the `hydra_links` database boundary for controlled global arrival guidance and per-Location training links. Stored destinations accept only HTTPS and an optional fixed `v` parameter. Rendered destinations preserve `v` and add only the public `lang` value and `from=hydra`; credentials, fragments, custom ports, arbitrary query parameters, Person/employee identifiers and tokens are rejected.

1. Keep the GitHub Pages portal and all existing public URLs active.
2. Store global arrival guidance and per-location training URLs as controlled database records in Hydra. **Implemented with permission and active-scope enforcement.**
3. Add a visible `Training / Hydra` link to authenticated worker, brigadier and coordinator navigation when the Hydra shell task is executed. **Implemented for the shared authenticated Hydra shell.**
4. Pass only the selected public language and `from=hydra` marker. Do not include Person, employee, location assignment or tokens in the public URL.
5. Open external links with safe browser attributes and a clear external-site label.
6. Monitor/redirect stable public URLs rather than silently replacing them.

No portal code, manifest or service worker is copied into authenticated Django routes.

## Later Django migration

Migration can start only after:

- authentication and Hydra scope tests pass;
- the `Location` data model is stable;
- public/private content ownership is approved;
- Django translation codes and the portal's `ua` alias are mapped explicitly;
- cache-control rules prevent private content caching;
- redirect and rollback plans protect all public URLs;
- native translation review is complete.

A safe sequence is:

1. reproduce public landing behavior in a separate anonymous Django route;
2. test nine languages, audio, links, mobile layout and accessibility;
3. publish redirects only after parity is accepted;
4. keep the static deployment available as rollback for at least one release cycle;
5. migrate training content site-by-site only when there is a business reason.

## Acceptance checks for future changes

- all four destination categories remain reachable;
- `lang` survives navigation;
- existing bookmarks and PWA installation remain valid or redirect safely;
- offline cache contains no authenticated response;
- 320 px mobile viewport has no horizontal overflow;
- keyboard/assistive labels work in every language;
- no personal identifier appears in public HTML, storage, cache or URL.
