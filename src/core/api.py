from fastapi import FastAPI

from src.schemas import (
    ApplicationPayload,
    AuditInfo,
    CaseStatus,
    SystemResponse,
)

app = FastAPI(title="MedLeaveAssist", version="1.0.0")


@app.post("/api/apply", response_model=SystemResponse)
def submit_application(payload: ApplicationPayload) -> SystemResponse:
    audit = AuditInfo(actor="system", rule_version="v1.0")
    return SystemResponse(
        case_id=payload.case_id,
        status=CaseStatus.DRAFT,
        message="申请已受理，正在等待材料提取",
        audit=audit,
    )
