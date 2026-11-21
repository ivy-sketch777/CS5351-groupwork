from typing import Literal, Optional

from pydantic import BaseModel, Field


class ReviewDecisionRequest(BaseModel):
    decision: Literal["approve", "reject"] = Field(
        ..., description="复核结论：approve 或 reject"
    )
    reason: str = Field(..., min_length=1, description="复核理由")


class SupplementRequest(BaseModel):
    additional_text: str = Field(..., min_length=1, description="补充材料说明")
    attachment_url: Optional[str] = Field(None, description="补充附件存储路径/URL (可选)")
