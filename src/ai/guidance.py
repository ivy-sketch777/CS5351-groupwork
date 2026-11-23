"""Student-facing templates using caller-provided policy facts (REQ-FR-005)."""

from src.schemas import PolicyDecision, PolicyResult


def student_guidance(decision: PolicyDecision) -> str:
    if decision.missing_items:
        items = '; '.join(dict.fromkeys(decision.missing_items))
        message = f'Please provide or correct the following so we can continue: {items}.'
    elif decision.result is PolicyResult.FAIL_CLOSED:
        message = 'Please check and correct your submission, or contact student support for help.'
    elif decision.result is PolicyResult.ROUTE_TO_REVIEW:
        message = 'Your submission needs a manual review. We may ask for more information.'
    else:
        message = 'There is nothing else to provide at this step.'
    if decision.rule_ids_fired:
        message += f" (Rules: {', '.join(decision.rule_ids_fired)})"
    return message
