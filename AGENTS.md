# AGENTS.md - Agent Governance & Project Rules

## 1. 项目背景与核心原则 (Project Overview)
本项目是 CS5351 校园病假助手 (MedLeaveAssist)。
最高红线（绝对不可违反）：AI 仅用于文本提取，严禁 AI 决定请假结果！所有判定必须由确定性代码或人工完成。任何接口绝不允许返回“假成功”。

## 2. 架构与数据契约 (Architecture & Contracts)
- 所有模块的数据流转必须严格遵循 `src/schemas.py` 中的 Pydantic 模型。
- 绝对禁止在代码中自行捏造新的数据结构，或修改 `schemas.py` 中的已有字段。
- 必须遵守低耦合原则，不得跨模块直接调用内部函数（必须通过接口）。

## 3. 核心需求字典 (Requirements Dictionary)
(注：AI 不具备上下文记忆，遇到需求 ID 必须查阅此处)
- REQ-FR-001：接收包含学号、课程代码、日期范围、原因文本、可选附件URL的申请数据。
- REQ-FR-002：AI 提取医疗证明信息，必须输出 `ExtractionResult` 结构，不可决定请假结果。
- REQ-FR-003：动态规则引擎，根据请假天数（如>3天转人工）返回 `PolicyDecision` 结构。
- REQ-FR-004：状态机流转（draft / pending_docs / in_review / approved / rejected / failed），绝不能返回假成功。
- REQ-INV-001：未经规则引擎通过，绝不自动批准。
- REQ-SEC-001：所有进入系统的自由文本必须经过安全清理（防 Prompt 注入）。
- REQ-GOV-001：每次决策必须记录审计信息（操作者、规则版本、模型版本）。

## 4. 模块划分与修改边界 (Module Boundaries)
本项目由 5 名成员并行开发，你（Agent）必须严格限制在当前用户的模块内，严禁越权修改其他文件夹的代码！
- `src/core/`：核心链路与状态机（成员 1 负责，当前主攻方向）。
- `src/policy/`：规则引擎（成员 2 负责）。
- `src/ai/`：AI 提取与摘要组件（成员 3 负责）。
- `src/security/` & `src/governance/`：安全与治理（成员 4 负责）。
- `test/` & `.github/`：测试与 CI/CD（成员 5 负责）。

## 5. Agent 工作流限制 (Workflow Rules)
1. 先计划，后编码**：每次接到新任务，必须先输出执行计划（接口设计、逻辑走向），等待人类回复“批准”后，才能修改代码。
2. 测试先行：每次新增函数，必须同时生成对应的离线测试代码。
3. Mock 优先：在集成前，若依赖其他模块（如调用规则引擎），必须使用 Mock 数据，禁止直接去写别人的模块。
4. 禁止裸写 SQL：所有数据库操作必须使用 ORM。