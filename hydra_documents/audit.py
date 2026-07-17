from dataclasses import dataclass
from hashlib import sha256

from hydra_documents.models import DocumentAccessLog


@dataclass(frozen=True)
class AccessContext:
    ip_address: str | None
    user_agent_sha256: str


def access_context_from_request(request):
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    return AccessContext(
        ip_address=request.META.get("REMOTE_ADDR") or None,
        user_agent_sha256=(
            sha256(user_agent.encode("utf-8")).hexdigest() if user_agent else ""
        ),
    )


def log_access(
    *, actor, context, document_uuid, action, outcome, reason, document=None, detail=""
):
    return DocumentAccessLog.objects.create(
        document=document,
        document_uuid=document_uuid,
        actor=actor,
        action=action,
        outcome=outcome,
        reason=reason,
        detail=detail[:255],
        ip_address=context.ip_address,
        user_agent_sha256=context.user_agent_sha256,
    )
