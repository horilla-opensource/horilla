from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render


def contracts_view(request):
    return render(request, "external_iframe.html", {"url": "https://contracts.ccdocs.com"})


def payroll_app_view(request):
    # Top-level redirect instead of iframe: payroll.ccdocs.com gates the
    # app behind Google OAuth, and accounts.google.com refuses to render
    # in a frame (X-Frame-Options: DENY), surfacing a Google 403 inside
    # the Horilla shell.
    return redirect("https://payroll.ccdocs.com/")


def hiring_view(request):
    return render(request, "external_iframe.html", {"url": "/hiring/api/admin/auto-login?token=SuperSecretAdminAuthSecretToken"})


def all_messages_view(request):
    """Unified candidate communications inbox — embeds inbox.ccdocs.com/conversations."""
    return render(request, "external_iframe.html", {"url": "https://inbox.ccdocs.com/conversations?embed=1"})


@login_required
def candidate_inbox_notifications(request):
    """
    Return the 20 most recent inbound candidate communications, grouped by
    candidate (latest message per candidate), with unread counts.
    Results are rendered as an HTML partial for HTMX inclusion in the
    notification tray and the "All Notifications" sidebar.

    Query the candidate_communications table directly — it lives in the
    same 'horilla' Postgres DB that Django already connects to.
    """
    with connection.cursor() as cur:
        cur.execute("""
            WITH latest AS (
                SELECT DISTINCT ON (candidate_id)
                    candidate_id,
                    candidate_name,
                    channel,
                    subject,
                    body,
                    created_at,
                    (
                        SELECT COUNT(*)::int
                        FROM candidate_communications cc2
                        WHERE cc2.candidate_id = cc.candidate_id
                          AND cc2.is_read = FALSE
                          AND cc2.direction = 'inbound'
                    ) AS unread_count
                FROM candidate_communications cc
                WHERE direction = 'inbound'
                ORDER BY candidate_id, created_at DESC
            )
            SELECT
                l.candidate_id,
                l.candidate_name,
                l.channel,
                l.subject,
                left(l.body, 120)  AS preview,
                l.created_at,
                l.unread_count
            FROM latest l
            ORDER BY l.created_at DESC
            LIMIT 20
        """)
        rows = cur.fetchall()

    messages = [
        {
            "candidate_id": r[0],
            "candidate_name": r[1] or "Unknown",
            "channel": r[2],
            "subject": r[3] or "",
            "preview": (r[4] or "").strip()[:100],
            "created_at": r[5],
            "unread_count": r[6],
            # Horilla canonical candidate-profile URL
            "profile_url": f"/recruitment/candidate-view/{r[0]}/",
        }
        for r in rows
    ]

    return render(
        request,
        "notification/candidate_inbox_items.html",
        {"inbox_messages": messages},
    )


@login_required
def candidate_inbox_unread_count(request):
    """JSON: total unread inbound candidate communications."""
    with connection.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*)::int FROM candidate_communications "
            "WHERE is_read = FALSE AND direction = 'inbound'"
        )
        count = cur.fetchone()[0]
    return JsonResponse({"count": count})
