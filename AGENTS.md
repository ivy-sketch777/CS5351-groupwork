# AGENTS.md - Agent Governance & Project Rules

## 1. 项目背景与核心原则 (Project Overview)
本项目是 CS5351 校园病假助手 (MedLeaveAssist)。
最高红线（绝对不可违反）：AI 仅用于文本提取，严禁 AI 决定请假结果！所有判定必须由确定性代码或人工完成。任何接口绝不允许返回“假成功”。

## 2. 架构与数据契约 (Architecture & Contracts)
- 所有模块的数据流转必须严格遵循 `src/schemas.py` 中的 Pydantic 模型。
- 绝对禁止在代码中自行捏造新的数据结构，或修改 `schemas.py` 中的已有字段。
- 必须遵守低耦合原则，不得跨模块直接调用内部函数（必须通过接口）。

## 3. 核心需求字典 (Requirements Dictionary)
(注：AI 不具备上下文记忆，遇到需求 ID 必须查阅此处；完整溯源见 `docs/trace-matrix.md`)

**功能 (FR)**
- REQ-FR-001：接收含学号、课程代码、日期范围、原因文本、可选附件URL的申请，必填齐全才接受并生成唯一 Case ID。
- REQ-FR-002：AI 从医疗证明提取医院名、就诊日期、建议休息天数、诊断短语，仅输出 `ExtractionResult` 严格 JSON，不做决定。
- REQ-FR-003：动态规则引擎返回 `PolicyDecision`（pass / fail-closed / route-to-review）及触发的 Rule ID，规则可配置。
- REQ-FR-004：状态流转 draft / pending_docs / in_review / approved / rejected / failed，异常绝不能显示“假成功”。
- REQ-FR-005：材料缺失或校验失败时生成自然语言引导提示，引导学生补充材料。
- REQ-FR-006：为辅导员生成含姓名、天数、日期、诊断、材料状态的智能摘要。
- REQ-FR-007：同一课程超过 3 个连续教学日必须转 MANUAL REVIEW，不得自动批准。
- REQ-FR-008：日期/证明等关键字段无法确立时交人工或拒绝，不得幻觉编造。

**不变量 (INV)**
- REQ-INV-001：未经确定性 Policy Checker 确认强制规则通过，绝不自动批准。
- REQ-INV-002：AI 输出不是资格/日期/材料完整性的最终权威；结果必须归因于 Rule ID 或人工 ID。
- REQ-INV-003：同一学生同一时间段禁止重叠的已批准病假（0 双重分配）。
- REQ-INV-004：不得编造源文档中不存在的医疗事实（日期、休息天数、诊断）。
- REQ-INV-005：确定性——相同输入必须产生相同 Outcome Class，不因 AI 非确定性翻转。

**架构 / 安全 / 成本 / 性能 / 质量 (ARCH / SEC / COST / PERF / QUAL)**
- REQ-ARCH-001：权威写入路径仅 PolicyChecker → ReviewQueue → LeaveStore；LLM 无权写 approved。
- REQ-ARCH-002：Extractor、Policy Engine、Summarizer 低耦合高内聚；改 Policy 不需改 AI 代码。
- REQ-ARCH-003：必须使用 CityUHK SSO，不得自建认证系统。
- REQ-ARCH-004：清洗数据与鉴权必须先于任何模型调用。
- REQ-SEC-001：所有自由文本进模型/规则前必须消毒（防 Prompt 注入）。
- REQ-SEC-002：发给 LLM 前脱敏学号、住址等无关隐私。
- REQ-SEC-003：原始医疗内容按最小权限可见，访问记录含操作者与时间。
- REQ-SEC-004：敏感上传工作副本结案后 30 天内清除。
- REQ-COST-001：平均 ≤1500 token/请求，单次硬上限 3000；简单请求走规则不调 LLM。
- REQ-PER-001：Policy Check（排除 LLM）p95 < 500ms。
- REQ-QUAL-001：面向学生的解释必须包含实际触发的 Rule ID。
- REQ-QUAL-002：冲突优先级见 §6。

**治理 (GOV)**
- REQ-GOV-001：每次决策记录操作者、规则版本、模型版本、Prompt 版本、结果与 Rule ID。
- REQ-GOV-002：低置信度、缺文档、红旗症状或规则冲突一律转人工复核。
- REQ-GOV-003：人工复核须展示证据、允许异议、支持升级，防止“橡皮图章”。
- REQ-GOV-004：派生值必须显示确切值并标注 `derived`。
- REQ-GOV-005：遵循 `.opencode/rules.md`；所有 Prompt 版本记录在 `prompts/prompt_v1.0.yaml`，CI 检查规范与版本文件。
- REQ-GOV-006：CI 阻断门 `ci.yml`；未通过 `test/offline/` 的 AI 生成代码由 GitHub 拒绝合并，不得伪造成功。
- REQ-GOV-007：`docs/trace-matrix.md` 将每个 FR 映射到代码文件与测试用例，100% 覆盖 FR 与 INV。

## 4. 模块划分与修改边界 (Module Boundaries)
本项目由 5 名成员并行开发，你（Agent）必须严格限制在当前用户的模块内，严禁越权修改其他文件夹的代码！
- `src/core/`：核心链路与状态机（成员 1 负责，当前主攻方向）。
- `src/policy/`：规则引擎（成员 2 负责）。
- `src/ai/`：AI 提取与摘要组件（成员 3 负责）。
- `src/security/` & `src/governance/`：安全与治理（成员 4 负责）。
- `test/` & `.github/`：测试与 CI/CD（成员 5 负责）。
- `prompts/`、`docs/`、`trace-matrix.md`：治理产物（成员 5 负责）；其他成员如需新增 Prompt 版本，必须追加 changelog 并同步 Trace Matrix。

## 5. Agent 工作流限制 (Workflow Rules)
1. 先计划，后编码：每次接到新任务，必须先输出执行计划（接口设计、逻辑走向），等待人类回复“批准”后，才能修改代码。
2. 测试先行：每次新增函数，必须同时生成对应的离线测试代码。
3. Mock 优先：在集成前，若依赖其他模块（如调用规则引擎），必须使用 Mock 数据，禁止直接去写别人的模块。
4. 禁止裸写 SQL：所有数据库操作必须使用 ORM（CI Gate A 用 AST 检查）。

## 6. CI 门禁与溯源 (CI Gate & Traceability)
- 唯一阻断 job 名为 `blocking-gate`，必须配置为 `main` 分支的 required status check；三个 gate（治理静态检查、完整离线套件、Trace Matrix 覆盖）全部通过才可合并。
- 严禁 `continue-on-error`、`|| true`、跳过测试；任何测试失败必须拒绝合并，绝不允许“假成功”。
- 负向演练与分支保护配置步骤见 `docs/ci-gate.md`。
- 全局溯源表见 `docs/trace-matrix.md`（根目录 `trace-matrix.md` 仅为指针）；新增需求或测试用例必须同步更新，由 Gate C 强制校验。
- **冲突解决优先级（REQ-QUAL-002）**：可靠性 → 输入边界安全 → 可问责性 → 成本。所有 ADR 与冲突处理记录必须引用此顺序；顺序不可调换。
