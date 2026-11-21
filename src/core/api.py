from typing import List

from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.database import CaseDB, get_db, init_db
from src.core.mock_policy import evaluate_policy
from src.core.models import ReviewDecisionRequest, SupplementRequest
from src.schemas import (
    ApplicationPayload,
    AuditInfo,
    CaseStatus,
    PolicyResult,
    SystemResponse,
)

app = FastAPI(title="MedLeaveAssist", version="1.0.0")

init_db()

MOCK_COUNSELOR_TOKEN = "MOCK-COUNSELOR"

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


def _build_audit() -> AuditInfo:
    return AuditInfo(actor="system", rule_version="v1.0")


def require_counselor(x_counselor_token: str = Header(default="")) -> str:
    if x_counselor_token != MOCK_COUNSELOR_TOKEN:
        raise HTTPException(status_code=401, detail="辅导员认证失败")
    return x_counselor_token


@app.post("/api/apply", response_model=SystemResponse)
def submit_application(
    payload: ApplicationPayload, db: Session = Depends(get_db)
) -> SystemResponse:
    decision = evaluate_policy(payload)
    target_status = _RESULT_TO_STATUS[decision.result]

    record = CaseDB(
        case_id=payload.case_id,
        student_id=payload.student_id,
        course_id=payload.course_id,
        start_date=payload.date_range.start_date,
        end_date=payload.date_range.end_date,
        reason_text=payload.reason_text,
        attachment_url=payload.attachment_url,
        status=target_status.value,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="案件已存在，请勿重复提交")
    db.refresh(record)

    return SystemResponse(
        case_id=record.case_id,
        status=CaseStatus(record.status),
        message=_STATUS_MESSAGE[target_status],
        audit=_build_audit(),
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
        audit=AuditInfo(actor=counselor_token, rule_version="v1.0"),
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

    record.reason_text = f"{record.reason_text}\n[补充] {request.additional_text}"
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
