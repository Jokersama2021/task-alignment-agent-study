# Task Shield：核心復現實作對照

來源：Jia et al., ACL 2025，DOI 10.18653/v1/2025.acl-long.1435。[正式 PDF](https://aclanthology.org/2025.acl-long.1435.pdf)。PDF 頁碼從 1 起；本文主文 pp.1–9、附錄 A–E pp.12–18 已實際閱讀，參考文獻 pp.10–11 未作完整核查。PDF 與文字提取保存於同目錄，雜湊見 `pdf-manifest.json`。以下是方法重述與本作業實作建議，不是作者原碼。

## 保留的核心機制

| 機制 | 原文位置 | 本作業應保留 |
|---|---|---|
| LLM 指令抽取 | §4.1 p.4；Fig.4 p.16 | 從 user／assistant／tool 訊息抽取顯式、隱含、巢狀可執行指令；保留參數與依賴。user 的結果建立或更新 Tu。 |
| LLM 貢獻評分 | §3–4 pp.3–4；Algorithm 1 p.13 | 每個候選 e 與每個使用者任務 t 配對，輸出 0–1 分數；S(e)=sum_t s(e,t)。主文以 S(e)=0 判不對齊；演算法寫 ≤ε，與主文一致時 ε=0，不能擅改成 0.5。 |
| Input Shield | §4.2 p.5；§5.3 p.7 | 檢查工具輸出中的指令，提供工具名與參數上下文；不對齊時把原工具輸出連同警示／使用者目標提醒交給 agent，並非直接刪除整段資料。 |
| Action Shield | §4.2 p.5；§5.3 p.7 | 執行前檢查工具名、參數對任務的貢獻；不對齊則阻止執行、回饋 agent 重新提議。參數指向錯誤對象也應評 0。 |
| 完整 Task Shield | §4.2 p.5 | 除上述兩端，還檢查 assistant 自然語言內容；只有工具 gate 的版本應稱 Action Shield，不能稱完整框架。 |

## Prompt 語意與輸出介面

這裡重述提示要點，不逐字複製論文長提示。可以自行撰寫較短提示，但需在 README 列為 prompt adaptation。

1. **抽取器（Fig.4）**：輸入訊息來源角色和內容；問題改寫成待完成的任務；依賴要保留；只回 JSON 字串陣列，沒有指令時回空陣列。不能把已知 attack label 傳給模型。
2. **內容評分器（Fig.5）**：輸入候選指令、角色／工具來源、Tu、對話歷史；考慮直接完成、必要中間步驟及合理嘗試，保持 system > user > assistant > tool 的信任層級。輸出每個使用者任務一項的 JSON 陣列，欄位為 `user_task_instruction`、`ContributeTo score`、`reason`。
3. **工具調用評分器（Fig.6）**：輸入工具名、完整參數、相關 assistant 內容、Tu、歷史；尤其核對收件人、檔案／目標等參數。原文要求同上述欄位，但範例第一欄誤寫 `task_instruction`，實作應統一欄位並記錄這一處格式正規化。
4. **回饋（Fig.7）**：指出具體不對齊指令／調用，要求不要執行，提醒尚待完成的原使用者任務。主文只說多輪修正，沒有給出可確認的最大重試次數；本作業需自行預先固定 retry budget 並標為實作選擇。

建議另存每次抽取／評分的原始模型回應、解析結果、分數和理由。JSON 解析失敗、空 Tu、漏行、越界數字均應獨立記錄；採何種失敗策略是本作業設計，不能冒稱論文明定。輸入不得包含正解、attack label、預期分數或 validator 結果。

## 精確比較條件與可引用數字

原文 §5 p.5：每個任務一次 trial；Appendix C.4 p.15：shield temperature=0.0。模型為 gpt-4o-2024-05-13、gpt-4o-mini-2024-07-18、gpt-3.5-turbo-0125；主要設定以與 agent 相同模型作 shield，§5.4 另比較不同 defender。No Defense 數據取自 AgentDojo 已有原始紀錄，並非所有行在完全相同時間重新執行。

| 原表與條件 | No Defense | Task Shield | 正確解讀 |
|---|---|---|---|
| Table 1 p.6，GPT-4o，Important Instructions，Overall | U 50.08；ASR 47.69 | U 69.79；ASR 2.07 | 單位 %；U 是攻擊下合法任務成功率，非 clean utility。 |
| Table 2(a) p.8，同上 | CU 69.07；U 50.08；ASR 47.69 | CU 73.20；U 69.79；ASR 2.07 | CU 只在無攻擊環境計算，與 attacked-case 分母不同。 |
| Table 2(b) p.8，GPT-4o-mini，Overall | CU 68.04；U 49.92；ASR 27.19 | CU 68.04；U 54.53；ASR 2.23 | 不可當成本地小模型的預期成績。 |
| Table 3 p.8，GPT-4o-mini，Slack，Action Shield | CU 66.67；U 52.38；ASR 7.62 | N/A | 此行是原文 Action Shield 結果。 |
| Table 3 p.8，同設定，Input Shield | CU 71.43；U 63.80；ASR 4.76 | N/A | 此行是原文 Input Shield 結果。 |
| Table 3 p.8，同設定，完整 Task Shield | N/A | CU 66.67；U 50.48；ASR 0.95 | 效用和安全均需報，不能只報低 ASR。 |

ASR 的語意是攻擊者指定目標達成；CU/U 是使用者任務達成，不是 shield 分類 accuracy。若使用固定候選行為而沒有 agent 端到端執行，應報 aligned-action acceptance、misaligned-action block 等機制級指標；不要借用原表的 ASR/U 名稱冒充端到端評估。

原文存在應保留的細節差異：Table 2 caption 用 Important Messages，而正文用 Important Instructions；Table 4 的 GPT-4o defender U=50.48 與 Table 2(a) GPT-4o Slack U=64.76 不一致，未得到作者說明前不要合併這兩個值；§5.3 的 No Restate 段落以 Input Shield 的 63.80 作比較起點，並非完整 Task Shield 的 50.48。本作業直接引用 Table 1／2／3 的明確行列即可。

## 合理簡化與不可替代項（本審計建議）

- **可以縮小**：本地合成離線環境、少量固定任務、較短上下文、固定攻擊樣式、有限修正回合；完整列出不同於原論文的模型／環境／規模，稱「核心機制簡化復現」。
- **必須保留**：真實模型抽取與語意貢獻評分、逐使用者任務分數、工具來源上下文、錯誤參數檢查；評分器只看任務與歷史，不看標籤。
- **規則的合適用途**：JSON 型別／範圍驗證、執行 gate、狀態 validator、統計與記錄。規則不應替代 LLM 的對齊判斷後仍稱 Task Shield。
- **原文未驗證的外推**：開源本地 backbone、不同攻擊分布、廣泛對抗適應攻擊。§8 p.9 直接指出弱模型／對抗探測可導致抽取或評分錯誤、額外 LLM 調用有成本、主實驗僅 GPT 家族和 AgentDojo。這些應列入本作業限制。
- **設計自有任務時**：包含合法準備步驟、看似無害但無關的指令、錯收件人／錯檔案參數、同名近似目標；凍結測試集，避免根據測試輸出反覆改 prompt 追求高分。攻擊均限沙箱虛構資料與無外部副作用工具。

本次未找到可由作者來源確認的官方 Task Shield 程式庫。搜尋結果存在第三方 scaffold，明示非作者原碼；未用其行為作為原論文依據。
