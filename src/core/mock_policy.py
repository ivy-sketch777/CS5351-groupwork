from src.schemas import ApplicationPayload, PolicyDecision, PolicyResult


def evaluate_policy(payload: ApplicationPayload) -> PolicyDecision:
    """Mock 规则引擎（替代未完成的 M2 模块）。

    仅做确定性判定，不产出批准结果。超过 3 天转人工，其余放行待材料。
    """
    start = payload.date_range.start_date
    end = payload.date_range.end_date
    days = (end - start).days + 1

    if days <= 0:
        return PolicyDecision(
            result=PolicyResult.FAIL_CLOSED,
            rule_ids_fired=["RULE-MOCK-INVALID-RANGE"],
            reason="请假日期范围无效",
        )

    if days > 3:
        return PolicyDecision(
            result=PolicyResult.ROUTE_TO_REVIEW,
            rule_ids_fired=["RULE-MOCK-REVIEW"],
            reason="请假超过3天，转人工复核",
        )

    return PolicyDecision(
        result=PolicyResult.PASS,
        rule_ids_fired=["RULE-MOCK-PASS"],
        reason="请假天数在自动阈值内",
    )
