from src.policy.models import Rule, RuleSet
from src.schemas import PolicyResult


def _make_rule(**overrides):
    kwargs = dict(
        id="RULE-TEST-001",
        priority=10,
        description="test rule",
        condition="days > 3",
        action=PolicyResult.ROUTE_TO_REVIEW,
        reason="test reason",
    )
    kwargs.update(overrides)
    return Rule(**kwargs)


def test_add_missing_defaults_to_independent_lists():
    a = _make_rule()
    b = _make_rule()

    assert a.add_missing == []
    assert b.add_missing == []
    assert a.add_missing is not b.add_missing

    a.add_missing.append("medical_certificate")
    assert a.add_missing == ["medical_certificate"]
    assert b.add_missing == []


def test_action_is_policy_result_instance():
    rule = _make_rule(action=PolicyResult.PASS)

    assert isinstance(rule.action, PolicyResult)
    assert rule.action is PolicyResult.PASS


def test_ruleset_rules_default_to_independent_empty_lists():
    a = RuleSet(version="v1.0")
    b = RuleSet(version="v1.0")

    assert a.rules == []
    assert b.rules == []
    assert a.rules is not b.rules

    a.rules.append(_make_rule())
    assert len(a.rules) == 1
    assert b.rules == []


def test_rule_full_construction():
    rule = _make_rule(
        id="RULE-DURATION-001",
        priority=1,
        description="route to review when longer than 3 days",
        condition="days > 3",
        action=PolicyResult.ROUTE_TO_REVIEW,
        reason="leave longer than 3 days requires manual review",
        add_missing=["medical_certificate"],
        set_overlap=True,
    )

    assert rule.id == "RULE-DURATION-001"
    assert rule.priority == 1
    assert rule.description == "route to review when longer than 3 days"
    assert rule.condition == "days > 3"
    assert rule.action is PolicyResult.ROUTE_TO_REVIEW
    assert rule.reason == "leave longer than 3 days requires manual review"
    assert rule.add_missing == ["medical_certificate"]
    assert rule.set_overlap is True
