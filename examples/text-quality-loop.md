# Example: Text Quality Loop — Optimize Writing with a Checklist

Use automl's checklist mode to iteratively improve a piece of writing against a set of quality criteria. No shell commands needed — the agent evaluates its own output.

## Scenario

You have a README or article that needs quality improvement. You define what "good" looks like as a checklist, and automl iterates until the writing passes.

## When to Use Checklist Mode

Use checklist mode when quality is subjective and cannot be expressed as a shell command:
- Writing tone and clarity
- Marketing copy effectiveness
- Documentation completeness
- Style guide compliance

Use shell mode when quality is objective:
- Word count limits
- Required sections present
- Linting rules

## Command

```
/automl improve my README until it passes the quality checklist
evaluator: checklist
checklist:
  - Does the opening paragraph explain what the project does in one sentence?
  - Are there zero buzzwords like "revolutionary", "cutting-edge", or "best-in-class"?
  - Does the Quick Start section show a working command within 5 lines?
  - Is every claim backed by a concrete example or number?
scope: README.md
runs_per_iter: 3
max: 15
```

## Key Parameters for Checklist Mode

**runs_per_iter: 3** — the agent reads and scores the output 3 times per iteration, simulating different reader perspectives, then averages the scores. Use 3-5 for checklist mode to reduce variance.

**consecutive_passes: 3** — require 3 consecutive full-pass scores before marking as stable. Combined with `runs_per_iter: 3`, this means 9 total reads all passing before automl stops.

**max: 15** — allow up to 15 iterations. Writing tasks often need more iterations than code fixes.

## How Checklist Scoring Works

Each iteration:
1. The subagent revises `README.md` with one focused improvement
2. The subagent reads the result and answers each checklist item yes/no
3. Pass rate = (yes count) / (total items)
4. If pass rate improved → keep the revision
5. If pass rate dropped → revert to previous version
6. This repeats until all items pass in `runs_per_iter` consecutive reads

## Example Checklist Designs

**Marketing copy:**
```
checklist:
  - Does the headline include a specific number or concrete outcome?
  - Is the first sentence a specific pain point scenario, not a product description?
  - Does the CTA tell the user what happens next after clicking?
  - Are there zero phrases like "seamless", "intuitive", or "powerful"?
```

**Technical documentation:**
```
checklist:
  - Can a new user follow the Quick Start without reading anything else?
  - Does each code example include expected output?
  - Are all configuration options documented with their defaults?
  - Is there a troubleshooting section for the most common error?
```

**Blog post:**
```
checklist:
  - Does the opening hook present a concrete scenario rather than a general claim?
  - Is the main argument stated in the first 3 paragraphs?
  - Does the post end with a specific action the reader can take today?
  - Are there at least 2 concrete examples supporting the main argument?
```

## Monitoring Progress

```bash
cat .automl/*/state.json | jq .checkpoint_summary
```

The `checkpoint_summary` shows current pass rate per task and iteration count, so you can see the writing improving in real time.

## Changelog as Learning Record

The `.automl/{run_id}/changelog.md` records what changed in each iteration and why it helped or hurt. After the run, this is a useful record of which edits improved quality and which ones backfired.

---

# 範例：文字品質迴圈 — 用 Checklist 優化寫作（繁體中文）

使用 automl 的 checklist 模式，根據一組品質標準反覆改善文章。不需要 shell 指令 — agent 自己評估輸出品質。

## 場景

你有一份 README 或文章需要提升品質。你定義「好」的標準作為 checklist，automl 迭代直到寫作通過。

## 何時使用 Checklist 模式

品質主觀、無法用 shell 指令表達時，使用 checklist 模式：
- 寫作語氣與清晰度
- 行銷文案的說服力
- 文件完整性
- 風格指南合規性

品質客觀時，使用 shell 模式：
- 字數限制
- 必要段落是否存在
- Linting 規則

## 指令

```
/automl 改善我的 README，直到通過品質 checklist
evaluator: checklist
checklist:
  - 開頭段落是否用一句話說明專案是做什麼的？
  - 全文是否沒有「革命性」「業界領先」「顛覆性」等空洞詞彙？
  - Quick Start 段落是否在 5 行以內就能看到可執行的指令？
  - 每個論點是否有具體範例或數字支撐？
範圍: README.md
runs_per_iter: 3
max: 15
```

## Checklist 模式的關鍵參數

**runs_per_iter: 3** — agent 每輪讀取並評分輸出 3 次，模擬不同讀者視角，取平均分數。Checklist 模式建議設 3-5 以降低評分變異。

**consecutive_passes: 3** — 需要連續 3 次完全通過才算穩定達標。加上 `runs_per_iter: 3`，代表共需 9 次評讀全部通過，automl 才停止。

**max: 15** — 允許最多 15 輪迭代。寫作任務通常比程式碼修復需要更多輪。

## Checklist 評分機制

每輪迭代：
1. Subagent 對 `README.md` 做一個方向的改善
2. Subagent 閱讀結果，逐條回答 checklist yes/no
3. 通過率 = yes 數 / 總題數
4. 通過率提升 → 保留本輪改動
5. 通過率下降 → revert 回上一版
6. 重複直到所有項目在 `runs_per_iter` 次連續閱讀中全部通過

## Checklist 設計範例

**行銷文案：**
```
checklist:
  - 標題是否包含具體數字或明確成果？
  - 第一句是否是具體痛點場景，而不是產品描述？
  - CTA 是否告訴用戶點擊後會發生什麼？
  - 全文是否沒有「無縫」「直覺」「強大」等空洞詞彙？
```

**技術文件：**
```
checklist:
  - 新用戶是否可以只看 Quick Start 就上手，不需要讀其他部分？
  - 每個程式碼範例是否包含預期輸出？
  - 所有設定選項是否都有文件說明且標示預設值？
  - 是否有 troubleshooting 段落處理最常見的錯誤？
```

## 監控進度

```bash
cat .automl/*/state.json | jq .checkpoint_summary
```

`checkpoint_summary` 顯示每個 task 的當前通過率和迭代次數，讓你可以即時看到寫作品質的提升。

## Changelog 作為學習記錄

`.automl/{run_id}/changelog.md` 記錄每輪改動的內容和效果。跑完後，這份記錄能告訴你哪些改動有效、哪些反而讓品質下降，對未來的寫作改善很有參考價值。
