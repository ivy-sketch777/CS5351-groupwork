from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date

# ==========================================
# 基础枚举 (Enums) - 防止魔法字符串引发 Bug
# ==========================================

class CaseStatus(str, Enum):
    DRAFT = "draft"
    PENDING_DOCS = "pending_docs"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"

class PolicyResult(str, Enum):
    PASS = "pass"
    FAIL_CLOSED = "fail-closed"
    ROUTE_TO_REVIEW = "route-to-review"

# ==========================================
# 1. 申请表结构 (Application Payload)
# ==========================================

class DateRange(BaseModel):
    start_date: date = Field(..., description="请假开始日期")
    end_date: date = Field(..., description="请假结束日期")

class ApplicationPayload(BaseModel):
    case_id: str = Field(..., description="唯一案件ID (UUID)")
    student_id: str = Field(..., description="学生学号")
    course_id: str = Field(..., description="缺勤课程代码，例如 COMP999")
    date_range: DateRange = Field(..., description="请假日期范围")
    reason_text: str = Field(..., description="学生填写的请假原因")
    attachment_url: Optional[str] = Field(None, description="医疗证明附件的存储路径/URL (可选)")

# ==========================================
# 2. AI 提取结果结构 (Extraction Result) - 成员3用
# ==========================================

class ExtractedField(BaseModel):
    # 根据需求 REQ-GOV-004：生成/提取的值必须可见且标记为 derived
    value: Optional[str] = Field(None, description="提取出的实际值")
    derived: bool = Field(True, description="标记该字段由AI派生生成")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度 0-1")

class ExtractionResult(BaseModel):
    hospital_name: Optional[ExtractedField] = Field(None, description="医院名称")
    visit_date: Optional[ExtractedField] = Field(None, description="就诊日期")
    rest_days: Optional[ExtractedField] = Field(None, description="建议休息天数")
    diagnosis: Optional[ExtractedField] = Field(None, description="诊断短语")

# ==========================================
# 3. 规则引擎决策输出 (Policy Decision) - 成员2用
# ==========================================

class PolicyDecision(BaseModel):
    result: PolicyResult = Field(..., description="确定性规则引擎的最终判定")
    rule_ids_fired: List[str] = Field(default_factory=list, description="触发的规则ID列表，如 ['RULE-007']")
    missing_items: List[str] = Field(default_factory=list, description="缺失的材料项")
    is_overlapping: bool = Field(False, description="是否与已有批准的假期重叠")
    reason: str = Field(..., description="给用户或复核人员的明确原因")

# ==========================================
# 4. 统一状态与审计响应 (System Response) - 成员4参与
# ==========================================

class AuditInfo(BaseModel):
    # 根据需求 REQ-GOV-001：记录操作者、规则版本、模型版本、Prompt版本
    actor: str = Field(..., description="操作者身份：'system', 学生ID, 或辅导员ID")
    rule_version: str = Field(..., description="触发判定的规则库版本")
    model_version: Optional[str] = Field(None, description="使用的AI模型版本")
    prompt_version: Optional[str] = Field(None, description="使用的Prompt版本")

class SystemResponse(BaseModel):
    case_id: str = Field(..., description="唯一案件ID")
    status: CaseStatus = Field(..., description="当前系统状态")
    message: str = Field(..., description="返回给用户的提示信息（含友好提示）")
    audit: AuditInfo = Field(..., description="审计元数据")
