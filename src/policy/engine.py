from datetime import date, timedelta
from pathlib import Path

from src.policy.condition_eval import evaluate_condition
from src.policy.exceptions import PolicyConfigError
from src.policy.models import Rule, RuleSet
from src.policy.rule_loader import load_rules
from src.schemas import ApplicationPayload, PolicyDecision, PolicyResult

_DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "policy_v1.0.yaml"


def evaluate_policy(
    payload: ApplicationPayload,
    overlap_flag: bool = False,
    *,
    today: date | None = None,
) -> PolicyDecision:
    """Evaluate a leave application against the configured rule set.

    Rules are evaluated highest priority first. A ``fail-closed`` hit
    short-circuits immediately; otherwise all hits are aggregated with
    ``route-to-review`` winning over ``pass``. If no rule matches, the
    result defaults to ``fail-closed`` (never a fake success). Any error
    is converted to ``fail-closed``; this function never raises.
    """
    try:
        rule_set = load_rules(_DEFAULT_CONFIG_PATH)
        context = _build_context(payload, overlap_flag, today)
        rules = _sort_rules(rule_set.rules)
        return _run(rules, context, overlap_flag)
    except PolicyConfigError as exc:
        return _fail_closed(f"Policy evaluation failed: {exc}", overlap_flag)
    except Exception as exc:
        return _fail_closed(
            f"Unexpected policy evaluation error: {exc}", overlap_flag
        )


def _build_context(
    payload: ApplicationPayload, overlap_flag: bool, today: date | None
) -> dict:
    start = payload.date_range.start_date
    end = payload.date_range.end_date

    is_date_invalid = start > end
    if is_date_invalid:
        duration_days = 0
    else:
        duration_days = _count_teaching_days(start, end)

    has_evidence = bool(payload.attachment_url)

    context = {
        "duration_days": duration_days,
        "is_overlapping": overlap_flag,
        "is_date_invalid": is_date_invalid,
        "has_evidence": has_evidence,
    }
    if today is not None:
        context["today"] = today
    return context


def _count_teaching_days(start: date, end: date) -> int:
    """Count teaching days (Monday-Friday) between start and end inclusive.

    Weekends (Saturday/Sunday) are excluded. Public holidays are not
    considered. If the range contains no teaching day, returns 0.
    """
    count = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def _sort_rules(rules) -> list[Rule]:
    return sorted(rules, key=lambda rule: rule.priority, reverse=True)


def _run(rules, context: dict, overlap_flag: bool) -> PolicyDecision:
    fired: list[str] = []
    missing_items: list[str] = []
    route_reason: str | None = None
    route_fired = False
    pass_fired = False
    pass_reason: str | None = None
    overlap_fired = overlap_flag

    for rule in rules:
        if not evaluate_condition(rule.condition, context):
            continue

        fired.append(rule.id)
        for item in rule.add_missing:
            if item not in missing_items:
                missing_items.append(item)
        if rule.set_overlap:
            overlap_fired = True

        if rule.action == PolicyResult.FAIL_CLOSED:
            return PolicyDecision(
                result=PolicyResult.FAIL_CLOSED,
                rule_ids_fired=fired,
                missing_items=missing_items,
                is_overlapping=overlap_fired,
                reason=rule.reason,
            )

        if rule.action == PolicyResult.ROUTE_TO_REVIEW and not route_fired:
            route_fired = True
            route_reason = rule.reason

        if rule.action == PolicyResult.PASS and not pass_fired:
            pass_fired = True
            pass_reason = rule.reason

    if route_fired:
        return PolicyDecision(
            result=PolicyResult.ROUTE_TO_REVIEW,
            rule_ids_fired=fired,
            missing_items=missing_items,
            is_overlapping=overlap_fired,
            reason=route_reason,
        )

    if pass_fired:
        return PolicyDecision(
            result=PolicyResult.PASS,
            rule_ids_fired=fired,
            missing_items=missing_items,
            is_overlapping=overlap_fired,
            reason=pass_reason,
        )

    return PolicyDecision(
        result=PolicyResult.FAIL_CLOSED,
        rule_ids_fired=fired,
        missing_items=missing_items,
        is_overlapping=overlap_fired,
        reason="No policy rule matched; defaulting to fail-closed.",
    )


def _fail_closed(reason: str, overlap_flag: bool) -> PolicyDecision:
    return PolicyDecision(
        result=PolicyResult.FAIL_CLOSED,
        rule_ids_fired=[],
        missing_items=[],
        is_overlapping=bool(overlap_flag),
        reason=reason,
    )
