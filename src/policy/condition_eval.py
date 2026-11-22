import ast

from src.policy.exceptions import PolicyConfigError

_MAX_EXPR_LEN = 500
_MAX_NODES = 200

_ALLOWED_CONST_TYPES = (bool, int, type(None))

_ALLOWED_NODES = frozenset(
    {
        ast.Expression,
        ast.BoolOp,
        ast.UnaryOp,
        ast.Not,
        ast.Compare,
        ast.Name,
        ast.Constant,
    }
)


def evaluate_condition(expr: str, context: dict) -> bool:
    """Safely evaluate a whitelisted Python-syntax boolean expression.

    Only a strict subset of the AST is permitted. Any unsupported node,
    unknown variable, syntax error, or size limit breach raises
    ``PolicyConfigError`` (fail-closed). No ``eval``/``exec``/``compile``
    is ever used.
    """
    tree = _parse(expr)
    result = _eval_node(tree.body, context)
    return bool(result)


def _parse(expr: str) -> ast.Expression:
    if not isinstance(expr, str):
        raise PolicyConfigError("condition must be a string")
    if len(expr) > _MAX_EXPR_LEN:
        raise PolicyConfigError("condition expression is too long")

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise PolicyConfigError(f"invalid condition syntax: {exc}") from exc

    if sum(1 for _ in ast.walk(tree)) > _MAX_NODES:
        raise PolicyConfigError("condition expression is too complex")

    return tree


def _eval_node(node: ast.AST, context: dict):
    node_type = type(node)
    if node_type not in _ALLOWED_NODES:
        raise PolicyConfigError(
            f"unsupported expression node: {node_type.__name__}"
        )

    if isinstance(node, ast.Expression):
        return _eval_node(node.body, context)

    if isinstance(node, ast.BoolOp):
        return _eval_boolop(node, context)

    if isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, ast.Not):
            raise PolicyConfigError("unsupported unary operator")
        return not _eval_node(node.operand, context)

    if isinstance(node, ast.Compare):
        return _eval_compare(node, context)

    if isinstance(node, ast.Name):
        return _eval_name(node, context)

    if isinstance(node, ast.Constant):
        return _eval_constant(node)

    raise PolicyConfigError(
        f"unsupported expression node: {node_type.__name__}"
    )


def _eval_boolop(node: ast.BoolOp, context: dict) -> bool:
    if isinstance(node.op, ast.And):
        for value in node.values:
            if not _eval_node(value, context):
                return False
        return True

    if isinstance(node.op, ast.Or):
        for value in node.values:
            if _eval_node(value, context):
                return True
        return False

    raise PolicyConfigError("unsupported boolean operator")


def _eval_compare(node: ast.Compare, context: dict) -> bool:
    left = _eval_node(node.left, context)

    for op, comparator in zip(node.ops, node.comparators):
        right = _eval_node(comparator, context)
        if not _apply_compare(op, left, right):
            return False
        left = right

    return True


def _apply_compare(op: ast.cmpop, left, right) -> bool:
    try:
        if isinstance(op, ast.Eq):
            return left == right
        if isinstance(op, ast.NotEq):
            return left != right
        if isinstance(op, ast.Lt):
            return left < right
        if isinstance(op, ast.LtE):
            return left <= right
        if isinstance(op, ast.Gt):
            return left > right
        if isinstance(op, ast.GtE):
            return left >= right
    except TypeError as exc:
        raise PolicyConfigError("incompatible comparison operands") from exc

    raise PolicyConfigError(
        f"unsupported comparison operator: {type(op).__name__}"
    )


def _eval_name(node: ast.Name, context: dict):
    if node.id not in context:
        raise PolicyConfigError(f"unknown variable in condition: {node.id}")
    return context[node.id]


def _eval_constant(node: ast.Constant):
    if not isinstance(node.value, _ALLOWED_CONST_TYPES):
        raise PolicyConfigError("unsupported constant type in condition")
    return node.value
