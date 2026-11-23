from pathlib import Path

import yaml

from src.policy.exceptions import PolicyConfigError
from src.policy.models import Rule, RuleSet
from src.schemas import PolicyResult

_REQUIRED_FIELDS = ("id", "priority", "description", "condition", "action", "reason")
_OPTIONAL_FIELDS = ("add_missing", "set_overlap")
_ALLOWED_FIELDS = frozenset(_REQUIRED_FIELDS + _OPTIONAL_FIELDS)

_VALID_ACTIONS = frozenset(member.value for member in PolicyResult)

_RULE_CACHE: dict[str, RuleSet] = {}


def clear_cache() -> None:
    """Drop all cached rule sets."""
    _RULE_CACHE.clear()


def load_rules(path: str | Path) -> RuleSet:
    """Load and validate a rule set from a YAML file.

    Results are cached per resolved absolute path. Any problem (missing
    file, invalid YAML, missing/invalid fields, bad action) raises
    ``PolicyConfigError`` (fail-closed); nothing partial is ever returned
    or cached.
    """
    if not isinstance(path, (str, Path)):
        raise PolicyConfigError("rule path must be a string or Path")

    key = _normalize_path(path)
    cached = _RULE_CACHE.get(key)
    if cached is not None:
        return cached

    text = _read_file(key)
    data = _parse_yaml(text)
    rule_set = _build_ruleset(data)
    _RULE_CACHE[key] = rule_set
    return rule_set


def _normalize_path(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve())


def _read_file(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PolicyConfigError(f"rule file not found: {path}") from exc
    except OSError as exc:
        raise PolicyConfigError(f"cannot read rule file: {path}") from exc


def _parse_yaml(text: str):
    if not text.strip():
        raise PolicyConfigError("rule file is empty")

    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PolicyConfigError(f"invalid YAML: {exc}") from exc


def _build_ruleset(data) -> RuleSet:
    if not isinstance(data, dict):
        raise PolicyConfigError("rule file root must be a mapping")

    version = data.get("version")
    if not isinstance(version, str) or not version:
        raise PolicyConfigError("rule file missing or invalid 'version'")

    raw_rules = data.get("rules")
    if not isinstance(raw_rules, list):
        raise PolicyConfigError("rule file 'rules' must be a list")

    rules = [_build_rule(item, index) for index, item in enumerate(raw_rules)]
    return RuleSet(version=version, rules=rules)


def _build_rule(item, index: int) -> Rule:
    if not isinstance(item, dict):
        raise PolicyConfigError(f"rule #{index} must be a mapping")

    rule_id = item.get("id")
    label = rule_id if isinstance(rule_id, str) and rule_id else f"#{index}"

    unknown = set(item) - _ALLOWED_FIELDS
    if unknown:
        raise PolicyConfigError(
            f"rule {label} has unknown field(s): {sorted(unknown)}"
        )

    for name in _REQUIRED_FIELDS:
        if name not in item:
            raise PolicyConfigError(f"rule {label} missing field: {name}")

    rule_id = _require_str(item["id"], "id", label)
    description = _require_str(item["description"], "description", label)
    condition = _require_str(item["condition"], "condition", label)
    reason = _require_str(item["reason"], "reason", label)
    priority = _require_int(item["priority"], "priority", label)
    action = _parse_action(item["action"], label)

    add_missing = item.get("add_missing", [])
    if not isinstance(add_missing, list) or not all(
        isinstance(entry, str) for entry in add_missing
    ):
        raise PolicyConfigError(
            f"rule {label} 'add_missing' must be a list of strings"
        )

    set_overlap = item.get("set_overlap", False)
    if not isinstance(set_overlap, bool):
        raise PolicyConfigError(f"rule {label} 'set_overlap' must be a boolean")

    return Rule(
        id=rule_id,
        priority=priority,
        description=description,
        condition=condition,
        action=action,
        reason=reason,
        add_missing=list(add_missing),
        set_overlap=set_overlap,
    )


def _require_str(value, name: str, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PolicyConfigError(f"rule {label} field '{name}' must be a non-empty string")
    return value


def _require_int(value, name: str, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PolicyConfigError(f"rule {label} field '{name}' must be an integer")
    return value


def _parse_action(raw, label: str) -> PolicyResult:
    if not isinstance(raw, str) or raw not in _VALID_ACTIONS:
        raise PolicyConfigError(f"rule {label}: invalid action {raw!r}")
    return PolicyResult(raw)
