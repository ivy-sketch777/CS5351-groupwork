import builtins

import pytest

from src.policy.condition_eval import evaluate_condition
from src.policy.exceptions import PolicyConfigError


def _ctx(**overrides):
    base = {
        "duration_days": 4,
        "is_overlapping": False,
        "is_date_invalid": False,
        "has_evidence": True,
    }
    base.update(overrides)
    return base


def test_duration_end_to_end():
    assert evaluate_condition("duration_days > 3", _ctx(duration_days=4)) is True
    assert evaluate_condition("duration_days > 3", _ctx(duration_days=3)) is False


def test_and_with_bool_constant():
    expr = "duration_days > 7 and has_evidence == False"
    assert evaluate_condition(expr, _ctx(duration_days=9, has_evidence=False)) is True
    assert evaluate_condition(expr, _ctx(duration_days=9, has_evidence=True)) is False
    assert evaluate_condition(expr, _ctx(duration_days=2, has_evidence=False)) is False


def test_equality_with_true():
    assert evaluate_condition("is_overlapping == True", _ctx(is_overlapping=True)) is True
    assert evaluate_condition("is_overlapping == True", _ctx(is_overlapping=False)) is False
    assert evaluate_condition("is_date_invalid == True", _ctx(is_date_invalid=True)) is True


def test_short_leave():
    assert evaluate_condition("duration_days < 2", _ctx(duration_days=1)) is True
    assert evaluate_condition("duration_days < 2", _ctx(duration_days=2)) is False


def test_not_and_or():
    assert evaluate_condition("not is_overlapping", _ctx(is_overlapping=False)) is True
    assert evaluate_condition("not is_overlapping", _ctx(is_overlapping=True)) is False
    assert evaluate_condition(
        "is_overlapping or is_date_invalid",
        _ctx(is_overlapping=False, is_date_invalid=True),
    ) is True
    assert evaluate_condition(
        "is_overlapping or is_date_invalid",
        _ctx(is_overlapping=False, is_date_invalid=False),
    ) is False


def test_chained_comparison():
    assert evaluate_condition("1 < duration_days < 9", _ctx(duration_days=4)) is True
    assert evaluate_condition("1 < duration_days < 9", _ctx(duration_days=9)) is False
    assert evaluate_condition("1 < duration_days < 9", _ctx(duration_days=1)) is False


@pytest.mark.parametrize(
    "expr",
    [
        "__import__('os').system('echo hi')",
        "().__class__.__bases__",
        "open('x')",
        "lambda: 1",
        "[x for x in [1]]",
        "9 ** 9",
        "duration_days[0]",
        "foo > 1",
        "duration_days >",
        "'a' + 'b'",
        "duration_days + 1",
        "is_overlapping is True",
    ],
)
def test_rejected_expressions_raise_config_error(expr):
    with pytest.raises(PolicyConfigError):
        evaluate_condition(expr, _ctx())


def test_unknown_variable_is_fail_closed():
    with pytest.raises(PolicyConfigError):
        evaluate_condition("missing_var == True", _ctx())


def test_incompatible_operands_none_ordering_raises_config_error():
    with pytest.raises(PolicyConfigError):
        evaluate_condition("None < duration_days", _ctx())


def test_incompatible_operands_string_vs_int_raises_config_error():
    context = _ctx()
    context["duration_days"] = "four"
    with pytest.raises(PolicyConfigError):
        evaluate_condition("duration_days > 3", context)


def test_too_long_expression_rejected():
    expr = "duration_days > 0 and " * 100 + "duration_days > 0"
    with pytest.raises(PolicyConfigError):
        evaluate_condition(expr, _ctx())


def test_too_complex_expression_rejected():
    expr = " and ".join(["duration_days > 0"] * 60)
    with pytest.raises(PolicyConfigError):
        evaluate_condition(expr, _ctx())


def test_non_string_expression_rejected():
    with pytest.raises(PolicyConfigError):
        evaluate_condition(123, _ctx())


def test_no_builtin_execution_happens(monkeypatch):
    called = {"hit": False}

    def _guard(*args, **kwargs):
        called["hit"] = True
        raise AssertionError("builtin execution must not be used")

    monkeypatch.setattr(builtins, "eval", _guard)
    monkeypatch.setattr(builtins, "exec", _guard)

    assert evaluate_condition("duration_days > 3", _ctx(duration_days=4)) is True
    with pytest.raises(PolicyConfigError):
        evaluate_condition("open('x')", _ctx())

    assert called["hit"] is False
