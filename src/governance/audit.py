"""Decision audit metadata builders (REQ-GOV-001)."""

from __future__ import annotations

from src.schemas import AuditInfo, CaseStatus, SystemResponse


def build_audit(
    *,
    actor: str,
    rule_version: str,
    model_version: str | None = None,
    prompt_version: str | None = None,
) -> AuditInfo:
    """Build AuditInfo with required version fields (REQ-GOV-001)."""
    if not actor or not str(actor).strip():
        raise ValueError("actor is required")
    if not rule_version or not str(rule_version).strip():
        raise ValueError("rule_version is required")
    return AuditInfo(
        actor=str(actor).strip(),
        rule_version=str(rule_version).strip(),
        model_version=model_version,
        prompt_version=prompt_version,
    )


def build_system_response(
    *,
    case_id: str,
    status: CaseStatus,
    message: str,
    audit: AuditInfo,
) -> SystemResponse:
    """Assemble the unified SystemResponse used by the core path."""
    if not case_id:
        raise ValueError("case_id is required")
    return SystemResponse(
        case_id=case_id,
        status=status,
        message=message,
        audit=audit,
    )
