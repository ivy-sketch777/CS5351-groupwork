"""PII redaction tests (REQ-SEC-002)."""

from datetime import date

from src.schemas import ApplicationPayload, DateRange
from src.security.redact import REDACTED, redact_for_llm, redact_pii


def _payload(**kwargs) -> ApplicationPayload:
    base = dict(
        case_id="case-2",
        student_id="87654321",
        course_id="CS5351",
        date_range=DateRange(start_date=date(2026, 11, 10), end_date=date(2026, 11, 11)),
        reason_text="Fever",
        attachment_url=None,
    )
    base.update(kwargs)
    return ApplicationPayload(**base)


def test_student_id_digits_redacted():
    text = "My student id is 87654321 and I have a cold."
    out = redact_pii(text)
    assert "87654321" not in out
    assert REDACTED in out
    assert "cold" in out


def test_address_label_redacted():
    text = "住址: 九龙塘达之路83号 诊断: 上呼吸道感染"
    out = redact_pii(text)
    assert "达之路" not in out
    assert REDACTED in out
    assert "上呼吸道感染" in out


def test_english_address_redacted():
    text = "I live at 83 Tat Chee Avenue. Diagnosis: flu."
    out = redact_pii(text)
    assert "83 Tat Chee Avenue" not in out
    assert REDACTED in out
    assert "flu" in out


def test_redact_for_llm_never_includes_student_id():
    payload = _payload(
        student_id="87654321",
        reason_text="Fever, student id 87654321, address: 1 Main Street",
    )
    llm_text = redact_for_llm(payload, extracted_text="Hospital: Queen Mary")
    assert "87654321" not in llm_text
    assert payload.student_id not in llm_text
    assert "Fever" in llm_text or REDACTED in llm_text
