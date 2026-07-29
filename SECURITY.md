# Security Policy

Horilla takes security seriously. This document explains how to report vulnerabilities, which versions we support, what is in or out of scope, and how we handle disclosure and CVE assignment.

This policy applies to Horilla HR ([`horilla/horilla-hr`](https://github.com/horilla/horilla-hr)).

## Supported versions

| Version | Branch(es) | Security support |
|---------|------------|------------------|
| v2 | `2.0` (default), `dev/v2.0` (active development) | **Yes** — actively maintained |
| v1 | `1.0`, `master` | **Deprioritized** — fixes considered case-by-case at maintainer discretion; no guaranteed patch schedule. Prefer upgrading to v2. |

See [Discussion #1127](https://github.com/horilla/horilla-hr/discussions/1127) for background on this policy.

After v2 GA, we intend to treat v1 as **EOL for security** except for extraordinary cases (e.g. critical issues affecting customers we still host on v1). Reports that only affect unsupported lines will normally be closed with guidance to upgrade.

## Reporting a vulnerability

**Do not** open a public GitHub issue or discussion for a security vulnerability.
**Do not** disclose exploit details publicly until we have published a fix or explicitly agreed otherwise.

### How to report

Use **GitHub Private Vulnerability Reporting** only:

1. Open a [private vulnerability report](https://github.com/horilla/horilla-hr/security/advisories/new) on this repository.
2. Include enough detail for us to reproduce the issue (see below).

We do **not** accept or triage security vulnerability reports by email. General support inboxes are for product help, not vulnerability disclosure.

We aim to **acknowledge** valid reports within **72 hours**. Resolution time depends on severity and complexity; we will keep you informed via the private advisory thread.

### What to include

- Affected Horilla HR **version** or commit / Docker tag
- Environment notes (self-hosted Compose, reverse proxy, auth mode) — use variable *names* and redacted examples only
- Step-by-step reproduction (minimal PoC preferred)
- Impact (who can exploit it, and what they gain)
- Whether a fix or workaround is already known

**Never** paste live secrets, tokens, database dumps, or customer PII.

Reporter-supplied CVSS scores are helpful input; maintainers decide the final severity.

Please avoid dumping large batches of unverified findings without waiting for triage feedback on earlier reports.

## Scope

### In scope

- Vulnerabilities in **Horilla application code** shipped in this repository
- Unsafe **default configuration** that we ship (for example a publicly known default `SECRET_KEY` in production paths)
- Issues that are **authentically exploitable** with realistic privileges on a **supported** version

### Out of scope

We will normally **not** treat the following as Horilla product CVEs. We may still harden or document them when useful.

| Class | Notes |
|-------|--------|
| CSV / Excel formula injection | Spreadsheet clients interpret cell content; not a Horilla application bug |
| Privilege escalation by users who already administer users/roles | Trusted-admin capability by design |
| Issues only on EOL Python or EOL Horilla versions | Upgrade to a supported line |
| Pure deployment misconfiguration | Operator responsibility (`DEBUG=True`, open admin, weak secrets you set yourself). **Exception:** shipping an insecure default that works out of the box |
| Media / static XSS when files are served outside documented secure paths | Follow Docker / deployment docs; do not bypass Django `protected_media` with a raw `/media/` alias |
| Dependency CVEs with **no reachable path** in Horilla | Tracked via Dependabot when applicable |
| Third-party plugins or custom code not shipped by Horilla | Report to that project’s maintainers |
| Compromise of marketing sites, email, or social accounts | Operational incident response — not a product advisory |
| Demands for cash payment (“beg bounties”) | Credit only (see Rewards) |

### Grey areas

- Dynamic code paths used for payroll / exports: treated as **high priority** if a non-superuser can inject or trigger execution; if strictly limited to trusted admins, we still harden for v2 quality and may document the trust boundary
- Default secrets in images or quickstart docs: **in-scope product defects**

## Severity (guidance)

Final severity is decided by maintainers:

| Level | Examples |
|-------|----------|
| Critical | Unauthenticated RCE, unauthenticated auth bypass, mass data exposure without auth |
| High | Authenticated RCE, large-scale IDOR on PII/payroll, authenticated auth bypass |
| Medium | XSS requiring user interaction, limited IDOR, open redirect |
| Low | Low-impact issues, verbose errors without clear exploit path |

## Disclosure and CVE process

1. Private intake via GitHub Private Vulnerability Reporting (private advisory draft)
2. Triage: in scope? valid? duplicate? supported version?
3. Fix on a supported branch; coordinate disclosure with the reporter when practical
4. Publish a GitHub Security Advisory and **request a CVE ID via GitHub** when the issue meets our publish criteria
5. Credit the reporter in the advisory (unless anonymity is requested)

We use **GitHub as the CVE Numbering Authority** for Horilla HR advisories. We do not require reporters to self-request CVEs from MITRE; unsupported self-requests may be disputed.

**We publish a CVE when all of the following are true:**

- Affects a **supported** release
- Is **authentically exploitable** with realistic privileges
- Is in **Horilla code** or an unsafe default we ship
- Is **not** a duplicate of an already-published advisory for the same root cause

Historical issues that only affected v1 and are fixed (or EOL) in v2 are generally **closed without a new CVE**, with a short disposition note.

## Rewards

There is **no cash bug bounty** at this time. We offer public credit in advisories and release notes. A paid program may be considered later when triage capacity is stable.

## Security tooling

On this repository:

- **Private vulnerability reporting** — enabled (required intake path above)
- **Dependabot** — config lives in `.github/dependabot.yml` (PRs target `dev/v2.0`); alert/update features are enabled when available on the org/plan
- **Secret scanning / push protection** — enabled when available on the org/plan

These are operational controls for maintainers; they do not replace private reporting of product vulnerabilities.

## Contact

- Security reports: [GitHub Private Vulnerability Reporting](https://github.com/horilla/horilla-hr/security/advisories/new) only — see [Reporting a vulnerability](#reporting-a-vulnerability)
- Non-security questions about this policy: open a GitHub Discussion, or contact the maintainers through the project’s normal channels

## Disclaimer

The Horilla project and its maintainers assume no liability for security vulnerabilities reported or discovered. We greatly appreciate responsible disclosure that helps keep users safe.
