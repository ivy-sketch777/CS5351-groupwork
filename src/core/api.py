from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.database import CaseDB, get_db, init_db
from src.schemas import (
    ApplicationPayload,
    AuditInfo,
    CaseStatus,
    SystemResponse,
)

app = FastAPI(title="MedLeaveAssist", version="1.0.0")

init_db()


def _build_audit() -> AuditInfo:
    return AuditInfo(actor="system", rule_version="v1.0")


@app.post("/api/apply", response_model=SystemResponse)
def submit_application(
    payload: ApplicationPayload, db: Session = Depends(get_db)
) -> SystemResponse:
    record = CaseDB(
        case_id=payload.case_id,
        student_id=payload.student_id,
        course_id=payload.course_id,
        start_date=payload.date_range.start_date,
        end_date=payload.date_range.end_date,
        reason_text=payload.reason_text,
        attachment_url=payload.attachment_url,
        status=CaseStatus.DRAFT.value,
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
        message="申请已受理，正在等待材料提取",
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
