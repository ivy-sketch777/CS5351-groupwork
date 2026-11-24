from typing import Any, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.ai import extract, student_guidance
from src.ai.extractor import MIN_CONFIDENCE
from src.core.database import CaseDB, get_db, init_db
from src.core.models import ReviewDecisionRequest, SupplementRequest
from src.governance import build_audit, route_decision
from src.policy import evaluate_policy
from src.schemas import (
    ApplicationPayload,
    AuditInfo,
    CaseStatus,
    ExtractionResult,
    PolicyDecision,
    PolicyResult,
    SystemResponse,
)
from src.security import redact_for_llm, sanitize_application, sanitize_text

app = FastAPI(title="MedLeaveAssist", version="1.0.0")

init_db()

MOCK_COUNSELOR_TOKEN = "MOCK-COUNSELOR"

_FIELD_LABELS = {
    "hospital_name": "医院名称",
    "visit_date": "就诊日期",
    "rest_days": "建议休息天数",
    "diagnosis": "诊断",
}

_STATUS_MESSAGE = {
    CaseStatus.PENDING_DOCS: "申请已受理，正在等待材料提取",
    CaseStatus.IN_REVIEW: "申请已受理，正在人工复核",
    CaseStatus.FAILED: "申请处理失败，请检查后重新提交",
}

_RESULT_TO_STATUS = {
    PolicyResult.PASS: CaseStatus.PENDING_DOCS,
    PolicyResult.ROUTE_TO_REVIEW: CaseStatus.IN_REVIEW,
    PolicyResult.FAIL_CLOSED: CaseStatus.FAILED,
}


class _NoOpProvider:
    """离线安全的默认提取 provider：不做任何网络调用。"""

    model_version = "offline-noop"

    def count_input_tokens(self, *, instructions: str, document: str,
                           schema: dict[str, Any]) -> int:
        return 0

    def generate(self, *, instructions: str, document: str, schema: dict[str, Any],
                 max_output_tokens: int) -> tuple[str, int]:
        return "", 0


def get_extraction_provider() -> Any:
    """AI provider 依赖。默认返回离线 no-op；真实 provider 由集成环境覆盖。"""
    return _NoOpProvider()


def _build_audit(
    *,
    actor: str = "system",
    model_version: str | None = None,
    prompt_version: str | None = None,
) -> AuditInfo:
    """REQ-GOV-001: audit via governance helper (never invent local fields)."""
    return build_audit(
        actor=actor,
        rule_version="v1.0",
        model_version=model_version,
        prompt_version=prompt_version,
    )


def _is_simple_request(payload: ApplicationPayload) -> bool:
    document = (payload.reason_text or "").strip()
    return payload.attachment_url is None and len(document) < 10


def _extraction_has_values(extraction: ExtractionResult) -> bool:
    for name in ("hospital_name", "visit_date", "rest_days", "diagnosis"):
        field = getattr(extraction, name, None)
        if field is not None and field.value is not None:
            return True
    return False


def _apply_review_route(
    *,
    target_status: CaseStatus,
    extraction: ExtractionResult,
    policy: PolicyDecision,
) -> CaseStatus:
    """Apply governance routing without inventing APPROVED (ADR-002).

    Empty/skipped AI results (all-null fields) must not force in_review, or
    short-leave pending_docs flows break. Escalate when governance cites
    non-confidence reasons, or low confidence on fields that actually have values.
    Never override FAIL_CLOSED → failed.
    """
    if target_status in (CaseStatus.FAILED, CaseStatus.IN_REVIEW):
        return target_status

    route = route_decision(extraction=extraction, policy=policy)
    if not route.should_review:
        return target_status

    non_confidence = [r for r in route.reasons if not r.startswith("low_confidence")]
    if non_confidence or _extraction_has_values(extraction):
        return CaseStatus.IN_REVIEW
    return target_status


def _has_approved_overlap(db: Session, payload: ApplicationPayload) -> bool:
    new_start = payload.date_range.start_date
    new_end = payload.date_range.end_date
    existing = (
        db.query(CaseDB)
        .filter(
            CaseDB.student_id == payload.student_id,
            CaseDB.status == CaseStatus.APPROVED.value,
            CaseDB.start_date <= new_end,
            CaseDB.end_date >= new_start,
        )
        .first()
    )
    return existing is not None


def _build_message(base_message: str, rule_ids: List[str]) -> str:
    suffix = ", ".join(rule_ids) if rule_ids else "无"
    return f"{base_message}（触发规则：{suffix}）"


def _missing_extraction_hints(extraction: ExtractionResult) -> List[str]:
    """列出提取缺失/低置信度的字段，仅用于提示，绝不参与状态判定。"""
    hints = []
    for field_name, label in _FIELD_LABELS.items():
        field = getattr(extraction, field_name)
        if field is None or field.value is None or field.confidence < MIN_CONFIDENCE:
            hints.append(label)
    return hints


def _run_extraction(payload: ApplicationPayload, provider: Any) -> ExtractionResult:
    """REQ-SEC-001/002 + REQ-ARCH-004: only sanitized+redacted text reaches the model."""
    attachment_text = (payload.attachment_url or "").strip()
    document = redact_for_llm(payload, extracted_text=attachment_text)
    simple_request = _is_simple_request(payload)
    try:
        return extract(
            document,
            provider=provider,
            ai_allowed=True,
            simple_request=simple_request,
        )
    except Exception:
        return ExtractionResult()


def _build_guidance_hint(decision: PolicyDecision,
                         extraction: ExtractionResult) -> Optional[str]:
    hints = _missing_extraction_hints(extraction)
    if not hints and not decision.missing_items:
        return None
    parts = []
    if hints:
        parts.append("建议补充医疗信息：" + "、".join(hints))
    guidance = student_guidance(decision)
    if decision.missing_items:
        parts.append(guidance)
    return "；".join(parts)


def require_counselor(x_counselor_token: str = Header(default="")) -> str:
    if x_counselor_token != MOCK_COUNSELOR_TOKEN:
        raise HTTPException(status_code=401, detail="辅导员认证失败")
    return x_counselor_token


@app.post("/api/apply", response_model=SystemResponse)
def submit_application(
    payload: ApplicationPayload,
    db: Session = Depends(get_db),
    provider: Any = Depends(get_extraction_provider),
) -> SystemResponse:
    # Security gate before AI / policy (REQ-SEC-001, REQ-ARCH-004)
    payload = sanitize_application(payload)
    extraction = _run_extraction(payload, provider)

    overlap_flag = _has_approved_overlap(db, payload)
    decision = evaluate_policy(payload, overlap_flag=overlap_flag)
    target_status = _RESULT_TO_STATUS[decision.result]
    target_status = _apply_review_route(
        target_status=target_status,
        extraction=extraction,
        policy=decision,
    )

    record = CaseDB(
        case_id=payload.case_id,
        student_id=payload.student_id,
        course_id=payload.course_id,
        start_date=payload.date_range.start_date,
        end_date=payload.date_range.end_date,
        reason_text=payload.reason_text,
        attachment_url=payload.attachment_url,
        status=target_status.value,
        extraction_json=extraction.model_dump_json(),
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="案件已存在，请勿重复提交")
    db.refresh(record)

    message = _build_message(
        _STATUS_MESSAGE[target_status], decision.rule_ids_fired
    )
    hint = _build_guidance_hint(decision, extraction)
    if hint:
        message = f"{message} {hint}"

    model_version = getattr(provider, "model_version", None)
    return SystemResponse(
        case_id=record.case_id,
        status=CaseStatus(record.status),
        message=message,
        audit=_build_audit(model_version=model_version),
    )


@app.get("/api/status/{case_id}", response_model=SystemResponse)
def get_status(case_id: str, db: Session = Depends(get_db)) -> SystemResponse:
    record = db.get(CaseDB, case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="案件不存在")

    return SystemResponse(
        case_id=record.case_id,
        status=CaseStatus(record.status),
        message=f"当前状态：{record.status}",
        audit=_build_audit(),
    )


@app.get("/api/review/pending", response_model=List[SystemResponse])
def list_pending_reviews(
    db: Session = Depends(get_db),
    _: str = Depends(require_counselor),
) -> List[SystemResponse]:
    records = (
        db.query(CaseDB)
        .filter(CaseDB.status == CaseStatus.IN_REVIEW.value)
        .order_by(CaseDB.case_id)
        .all()
    )

    return [
        SystemResponse(
            case_id=record.case_id,
            status=CaseStatus(record.status),
            message=f"待人工复核：{record.case_id}",
            audit=_build_audit(),
        )
        for record in records
    ]


@app.post("/api/review/{case_id}/decision", response_model=SystemResponse)
def submit_review_decision(
    case_id: str,
    request: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    counselor_token: str = Depends(require_counselor),
) -> SystemResponse:
    record = db.get(CaseDB, case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="案件不存在")

    if record.status != CaseStatus.IN_REVIEW.value:
        raise HTTPException(
            status_code=400, detail="当前状态不允许审批，仅 in_review 可审批"
        )

    new_status = (
        CaseStatus.APPROVED
        if request.decision == "approve"
        else CaseStatus.REJECTED
    )
    record.status = new_status.value
    record.decision_reason = request.reason
    db.commit()
    db.refresh(record)

    verb = "已批准" if request.decision == "approve" else "已驳回"
    return SystemResponse(
        case_id=record.case_id,
        status=CaseStatus(record.status),
        message=f"复核{verb}，理由：{request.reason}",
        audit=_build_audit(actor=counselor_token),
    )


@app.post("/api/apply/{case_id}/supplement", response_model=SystemResponse)
def submit_supplement(
    case_id: str,
    request: SupplementRequest,
    db: Session = Depends(get_db),
) -> SystemResponse:
    record = db.get(CaseDB, case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="案件不存在")

    if record.status != CaseStatus.PENDING_DOCS.value:
        raise HTTPException(
            status_code=400, detail="当前状态不允许补充材料，仅 pending_docs 可补件"
        )

    clean_extra = sanitize_text(request.additional_text)
    record.reason_text = f"{record.reason_text}\n[补充] {clean_extra}"
    if request.attachment_url:
        record.attachment_url = request.attachment_url
    record.status = CaseStatus.IN_REVIEW.value
    db.commit()
    db.refresh(record)

    return SystemResponse(
        case_id=record.case_id,
        status=CaseStatus(record.status),
        message="补充材料已受理，重新进入人工复核队列",
        audit=_build_audit(),
    )
