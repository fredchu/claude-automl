# Skill Mapping 對照表

> automl 主 session 在 Phase 1 拆 task 時查此表指定 skill，不用每次從零判斷。
> 主 session 可根據具體情況覆寫，此表是預設建議。
> gstack 技能以 `/` 開頭（如 `/investigate`），superpowers/其他以 `:` 分隔（如 `engineering:code-review`）。

---

## Phase 1 — 拆解 + Review

| 場景 | 技能 | 說明 |
|------|------|------|
| **預設（有 plan 要 review）** | **`/autoplan`**（強制） | 自動跑 CEO + eng + design 三個 review，6 決策原則自動處理 mechanical decisions |
| 純程式碼、無 UI | `/autoplan` | 會自動跳過 design review |
| 輕量任務（直跳 Phase 2） | 不跑 | |

---

## Phase 2 — 怎麼改

| 任務類型 | 強制技能 | 說明 |
|---------|---------|------|
| **Bug fix（任何語言）** | **`/investigate`** | 四階段系統性 debug（investigate → analyze → hypothesize → implement）。注意：freeze hook 在 subagent 中不生效，受控範圍靠 automl prompt 約束 |
| **Swift bug fix** | **`/investigate`** | 同上，Swift 特定問題也走系統性 debug |
| Swift 新功能 | `swift-concurrency` 或 `swiftui-expert-skill` | 併發 / UI 專長 |
| 一般程式碼新功能 | `superpowers:test-driven-development` | TDD loop |
| 程式碼重構 | `engineering:architecture` | ADR + 架構分析 |
| 文案 / 文章撰寫 | `polish` | 帶 writing-style reference |
| Prompt / Skill 優化 | `superpowers:writing-skills` | |
| 設定檔調校（高風險） | **`/careful`** | 破壞性指令防護（rm -rf、DROP TABLE、force-push 等） |
| 設定檔調校（低風險） | `none`（附理由） | 純值替換，無需領域知識 |

---

## Phase 3 — 怎麼審

| 審查步驟 | 任務類型 | 強制技能 | 說明 |
|---------|---------|---------|------|
| **FINAL_VERIFICATION** | 預設 | `none` | 純跑 evaluator + risk scenario test cases |
| | web app 專案 | **`/qa-only`** | 三層 QA（quick/standard/exhaustive）+ health score |
| | 效能相關 | **`/benchmark`** | Core Web Vitals + bundle size regression 偵測 |
| **RISK_REVIEW** | 程式碼（一般） | **`/investigate`** | 用 investigate 的 trace 方法論分析風險場景 |
| | 安全敏感（auth/crypto/API key） | **`/cso`** | Chief Security Officer：secrets、supply chain、LLM trust boundary |
| | 非程式碼 | `design:design-critique` | |
| **CODE_REVIEW** | 程式碼 | **`/review`** | Pre-landing review：SQL safety + LLM trust + dependency security + 可 spawn subagent |
| | 有 UI 的專案 | **`/design-review`** | 視覺 QA：inconsistency、spacing、hierarchy |
| | 非程式碼（純文字） | `design:design-critique` | |

---

## `/investigate` 的特殊地位

`/investigate` 同時出現在 Phase 2（Bug fix）和 Phase 3（Risk Review），但用途不同：
- **Phase 2**：作為「怎麼改」的技能 — 系統性找到 root cause 再修
- **Phase 3**：作為「怎麼審」的技能 — 用 investigate 的 trace 方法論分析每個 risk scenario 的 code path

這不是重複，而是同一套方法論的兩種應用。

**注意**：`/investigate` 的 freeze hook（PreToolUse 攔截 Edit/Write）在 subagent 中不生效 — skill frontmatter hooks 不會傳遞到 subagent 執行環境。受控範圍的保護沿用 automl 現有的 TASK_LOOP_PROMPT 約束（「只改受控範圍內的檔案，範圍外一律不碰」），這在 v3 實戰中已被驗證有效。

---

## Methodology Skill（v5.5+）

`methodology_skill` 是獨立於領域 skill 的方法論技能，控制「怎麼做」的節奏。

| 條件 | methodology_skill | 說明 |
|------|-------------------|------|
| `required_tests` 非空 + `evaluator_semantic_type == "test_runner"` | `superpowers:test-driven-development` | 自動設定，強制 TDD 分段（RED→GREEN→REFACTOR） |
| `required_tests` 非空 + 非 test_runner | `null` | checklist/metric/eval_script 場景不需要 TDD |
| `required_tests` 為空或不存在 | `null` | 舊有行為不變 |

> Phase 1.5c 自動修復時會自動設定 methodology_skill，主 session 不需手動指定。

---

## 維護機制

- **誰更新**：automl 的維護者（用戶），在安裝新 skill 或 gstack 大版本更新時檢查對照表
- **更新頻率**：跟隨 automl 版本（不需要每次 gstack 更新都改）
- **不在對照表裡的 task 類型**：主 session 自行判斷，不阻塞流程。用完後建議用戶把新 mapping 加回表
- **skill 被移除或改名時**：Skill tool 會回傳 `Unknown skill` 錯誤，subagent 的第一輪會失敗，主 session 檢測到後標記為 subagent_error，需要用戶介入更新對照表
