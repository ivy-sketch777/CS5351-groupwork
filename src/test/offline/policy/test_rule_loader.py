from pathlib import Path

import pytest

from src.policy import rule_loader
from src.policy.exceptions import PolicyConfigError
from src.policy.rule_loader import clear_cache, load_rules
from src.schemas import PolicyResult

_VALID_YAML = """
version: "v1.0"
rules:
  - id: RULE-A
    priority: 900
    description: long leave
    condition: duration_days > 3
    action: route-to-review
    reason: long leave review
    add_missing:
      - medical_certificate
    set_overlap: false
  - id: RULE-B
    priority: 100
    description: short leave
    condition: duration_days < 2
    action: pass
    reason: short leave pass
"""

_CONFIG_PATH = (
    Path(__file__).resolve().parents[3] / "src" / "policy" / "config" / "policy_v1.0.yaml"
)


@pytest.fixture(autouse=True)
def _reset_cache():
    clear_cache()
    yield
    clear_cache()


def _write(tmp_path, content, name="policy.yaml"):
    target = tmp_path / name
    target.write_text(content, encoding="utf-8")
    return target


def test_loads_valid_yaml_into_ruleset(tmp_path):
    path = _write(tmp_path, _VALID_YAML)

    rule_set = load_rules(path)

    assert rule_set.version == "v1.0"
    assert len(rule_set.rules) == 2
    first = rule_set.rules[0]
    assert first.id == "RULE-A"
    assert first.priority == 900
    assert first.action is PolicyResult.ROUTE_TO_REVIEW
    assert first.add_missing == ["medical_certificate"]
    assert first.set_overlap is False


def test_loads_real_config_file():
    rule_set = load_rules(_CONFIG_PATH)

    assert rule_set.version == "v1.0"
    assert len(rule_set.rules) == 5
    assert [r.priority for r in rule_set.rules] == [1000, 900, 850, 800, 100]
    assert all(isinstance(r.action, PolicyResult) for r in rule_set.rules)


def test_cache_returns_same_object(tmp_path):
    path = _write(tmp_path, _VALID_YAML)

    first = load_rules(path)
    second = load_rules(path)

    assert first is second


def test_cache_hit_avoids_disk_read(tmp_path, monkeypatch):
    path = _write(tmp_path, _VALID_YAML)
    calls = {"count": 0}
    original = rule_loader._read_file

    def _counting(p):
        calls["count"] += 1
        return original(p)

    monkeypatch.setattr(rule_loader, "_read_file", _counting)

    load_rules(path)
    load_rules(path)

    assert calls["count"] == 1


def test_relative_and_absolute_path_share_cache(tmp_path, monkeypatch):
    path = _write(tmp_path, _VALID_YAML)
    monkeypatch.chdir(tmp_path)

    from_relative = load_rules("policy.yaml")
    from_absolute = load_rules(path)

    assert from_relative is from_absolute


def test_missing_file_raises(tmp_path):
    with pytest.raises(PolicyConfigError):
        load_rules(tmp_path / "nope.yaml")


def test_invalid_path_type_raises():
    with pytest.raises(PolicyConfigError):
        load_rules(None)


def test_empty_file_raises(tmp_path):
    path = _write(tmp_path, "   \n")

    with pytest.raises(PolicyConfigError):
        load_rules(path)


def test_invalid_yaml_syntax_raises(tmp_path):
    path = _write(tmp_path, "version: v1\nrules: [unclosed\n")

    with pytest.raises(PolicyConfigError):
        load_rules(path)


def test_root_not_mapping_raises(tmp_path):
    path = _write(tmp_path, "- just\n- a list\n")

    with pytest.raises(PolicyConfigError):
        load_rules(path)


def test_missing_version_raises(tmp_path):
    path = _write(tmp_path, "rules: []\n")

    with pytest.raises(PolicyConfigError):
        load_rules(path)


def test_rules_not_list_raises(tmp_path):
    path = _write(tmp_path, "version: v1\nrules: {}\n")

    with pytest.raises(PolicyConfigError):
        load_rules(path)


@pytest.mark.parametrize(
    "rules_block, marker",
    [
        (
            """
  - id: RULE-X
    description: d
    condition: c
    action: pass
    reason: r
""",
            "missing priority",
        ),
        (
            """
  - id: RULE-X
    priority: 900
    description: d
    condition: c
    action: unknown
    reason: r
""",
            "invalid action",
        ),
        (
            """
  - id: RULE-X
    priority: 900
    description: d
    condition: c
    action: PASS
    reason: r
""",
            "uppercase action",
        ),
        (
            """
  - id: RULE-X
    priority: 900
    description: d
    condition: c
    action: route_to_review
    reason: r
""",
            "underscore action",
        ),
        (
            """
  - id: RULE-X
    priority: high
    description: d
    condition: c
    action: pass
    reason: r
""",
            "non-int priority",
        ),
        (
            """
  - id: RULE-X
    priority: true
    description: d
    condition: c
    action: pass
    reason: r
""",
            "bool priority",
        ),
        (
            """
  - id: RULE-X
    priority: 900
    description: d
    condition: c
    action: pass
    reason: r
    priorty: 1
""",
            "unknown field typo",
        ),
    ],
)
def test_invalid_rule_entries_raise(tmp_path, rules_block, marker):
    path = _write(tmp_path, "version: v1\nrules:" + rules_block)

    with pytest.raises(PolicyConfigError):
        load_rules(path)


def test_rule_item_not_mapping_raises(tmp_path):
    path = _write(tmp_path, "version: v1\nrules:\n  - just-a-string\n")

    with pytest.raises(PolicyConfigError):
        load_rules(path)


def test_failure_is_not_cached(tmp_path):
    path = _write(tmp_path, "version: v1\nrules:\n  - bad\n")

    with pytest.raises(PolicyConfigError):
        load_rules(path)

    path.write_text(_VALID_YAML, encoding="utf-8")
    rule_set = load_rules(path)

    assert len(rule_set.rules) == 2
