# CI 阻断门说明（REQ-GOV-006）

## 1. 门禁组成

工作流 `.github/workflows/ci.yml` 只定义一个 job：`blocking-gate`。三个命名 gate 全部跑在同一 job 内，任一步失败 → job 失败 → PR 上的 required check 变红 → GitHub 拒绝合并。

| Gate | 命令 | 作用 |
| --- | --- | --- |
| A | `pytest test/offline/test_ci_governance.py -v --strict-markers` | 治理静态检查：无裸 SQL / 必须 ORM、Prompt 版本文件、`.opencode/rules.md`、模块边界、CI YAML 自检 |
| B | `pytest test/offline -q --strict-markers --junitxml=artifacts/junit.xml` | 完整离线套件（全体成员测试 + 契约 + 集成 + 溯源） |
| C | `pytest test/offline/test_trace_matrix.py -v --strict-markers` | Trace Matrix 100% 覆盖与引用有效性 |

门禁禁止项（由 `test_ci_workflow_is_a_hard_gate` 自动检查）：
`continue-on-error: true`、`|| true`、测试步骤上的 `if: always()` / `if: cancelled()`、改名或删除 `blocking-gate`、移除 `pytest test/offline`。

## 2. 仓库侧必做配置（管理员操作）

YAML 不能自己开启分支保护，必须由仓库管理员设置一次：

1. 打开 `Settings` → `Branches` → `Branch protection rules` → `Add rule`。
2. Branch name pattern 填 `main`。
3. 勾选 **Require a pull request before merging**（建议至少 1 个 approval）。
4. 勾选 **Require status checks to pass before merging**，搜索并选中精确名称 **`blocking-gate`**。
5. 勾选 **Require branches to be up to date before merging**（防止用过期提交绕过）。
6. 勾选 **Do not allow bypassing the above settings**；如需限制 force push，可同时勾选 **Block force pushes**。
7. `Add rule` / `Save changes`。

等价 CLI（需管理员 token，替换 `OWNER/REPO`）：

```bash
gh api -X PUT repos/OWNER/REPO/branches/main/protection \
  -f required_status_checks.strict=true \
  -f 'required_status_checks.contexts[]=blocking-gate' \
  -f enforce_admins=true \
  -f 'required_pull_request_reviews.required_approving_review_count=1' \
  -F restrictions=null
```

> 注意：required check 名称必须精确为 `blocking-gate`。改 job 名会导致该检查永远"缺失"，PR 同样无法合并——这正是期望的失败关闭行为。

## 3. 负向演练（REQ-GOV-006 Fit Criterion）

达成标准："故意打破测试（如伪造病假 JSON）会阻断 PR"。

演练步骤（在临时分支上进行，勿污染 `main`）：

1. `git switch -c gate-negative-drill`。
2. 任选一种破坏方式：
   - 在 `test/offline/` 新增一个必定失败的测试；
   - 临时把 `prompts/prompt_v1.0.yaml` 的 `version` 改成与文件名不一致；
   - 临时在 `src/core/database.py` 加入 `cursor.execute("SELECT ...")`；
   - 提交一个伪造病假 JSON（缺 `reason_text` 且带 `approved: true`）的测试用例。
3. 开 PR 到 `main`，观察 Checks：Gate A 或 Gate B 必须为红，`blocking-gate` 为红，Merge 按钮被禁用。
4. 删除临时分支；确认本地无残留改动：`git status --short`。

预期结果：任何一项破坏都会让 CI 失败。若 Merge 按钮仍可点击，说明第 2 节的分支保护未配置完成，先修配置再合并。

## 4. 失败处置 SOP

| 现象 | 处理 |
| --- | --- |
| Gate A 报裸 SQL | 改回 SQLAlchemy ORM（参考 `src/core/database.py`），不要静默忽略 |
| Gate A 报 Prompt 元数据缺失 | 更新 `prompts/prompt_v1.0.yaml`，并追加 changelog 条目 |
| Gate B 业务测试失败 | 由对应模块成员修复；QA 不得用 `skip` / `xfail` 掩盖 |
| Gate C 报 ID 缺失 | 更新 `docs/trace-matrix.md`；新增需求必须同步矩阵与测试引用 |
| 依赖安装失败 | 检查 `requirements.txt`；CI 使用 Python 3.10 |

## 5. 冲突解决优先级（REQ-QUAL-002）

可靠性 → 输入边界安全 → 可问责性 → 成本。
与 AGENTS.md §6 一致；任何门禁例外申请必须按此顺序论证。
