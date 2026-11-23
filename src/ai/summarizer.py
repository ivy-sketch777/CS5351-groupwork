"""Deterministic, advisory summary for an authorized counsellor (REQ-FR-006)."""

from src.schemas import DateRange, ExtractionResult


def counsellor_summary(extraction: ExtractionResult, *, student_name: str | None = None,
                        leave_days: int | None = None, date_range: DateRange | None = None,
                        documents_complete: bool | None = None) -> str:
    """Leave duration and evidence status are supplied by the caller, not inferred."""
    unknown = 'not available'
    duration = (f'{leave_days} day(s)' if type(leave_days) is int and leave_days > 0
                else unknown)
    dates = (f'{date_range.start_date} to {date_range.end_date}' if date_range
             and date_range.start_date <= date_range.end_date else unknown)
    diagnosis = (f'{extraction.diagnosis.value} (derived)' if extraction.diagnosis
                 and extraction.diagnosis.value else unknown)
    status = ('complete' if documents_complete is True else
              'incomplete' if documents_complete is False else unknown)
    return (f'Student: {student_name or unknown}. Requested leave: {duration}. '
            f'Dates: {dates}. Diagnosis: {diagnosis}. Documents: {status}.')
