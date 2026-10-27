# 五篇核心論文結構化比較草稿

統一參考編號與完整書目見 `references.json`；以下依原文實際閱讀整理。所有文獻成績均是作者報告，並非本作業重跑結果。逐頁覆蓋、未讀部分與原文差異見 `reading-coverage.json`；不把跨研究成功率直接排序。

| 論文／角色 | 問題與方法 | 評測單位／規模 | 指標及判定 | 優點與限制 | 本作業可用位置 |
|---|---|---|---|---|---|
| InjecAgent [4]；早期工具安全 benchmark | 固定初始工具回應後，觀察注入誘導的動作；基礎與增強提示 | 17 使用者工具 × 62 攻擊工具，共 1054 案例；兩類攻擊；30 agents | ASR-valid 排除無效輸出，ASR-all 包含全部；解析工具調用；竊取有擷取／傳送兩步 | 控制清楚；假設初始工具成功，未執行完整有狀態環境，固定提示與簡化互動限制外推 | 分開格式錯誤、語意錯誤與實際執行；勿將簡化組件指標稱原 ASR |
| AgentDojo [5]；動態環境 | 智能體自主調用讀寫工具；使用者／攻擊者目標分開定義 | 4 合成環境、97 使用者任務、629 user/injection 配對案例 | benign utility、utility under attack、targeted ASR；程式檢查模型輸出與狀態變化 | 可擴充且檢查可重跑；任務／條件依賴人工，初始攻防不代表自適應最壞情況 | 明確 final-state validator、任務合約與指標分母 |
| Task Shield [7]；防禦 | LLM 抽取指令／建立 Tu，再逐任務評估貢獻；工具輸入回饋與動作前攔截 | AgentDojo 四套件；主要 GPT-4o／mini；每任務一次；另做 Input／Action／No Restate 消融 | CU、U、targeted ASR；零總貢獻判不對齊；原文另報延遲 | 任務對齊有可追查中間結果；仍依賴模型抽取／評分，可誤判，增加推論成本；未驗證開源模型 | 保留真實 LLM 抽取、逐 Tu 分數與執行 gate 的核心組件縮小復現 |
| AGENTVIGIL [9]；自動紅隊 | MCTS 式種子選擇、LLM 變異、ASR＋新覆蓋獎勵 | AgentDojo fuzzing 142／test 173；VWA-adv 99／100；不同突變預算 | 成功回饋、覆蓋；選定 top-5 seeds 的聯集轉移結果另報 | 對固定提示評估提出更強測試；查詢成本較高，跨模型轉移不一致 | 固定測試集只能支持有限結論；優化、轉移和 held-out 結果分離 |
| WASP [10]；Web 端到端評測 | 在可控網站中限制攻擊者只能改一般使用者內容；文字／網址型注入 | GitLab、Reddit 類環境；文中報 84 攻擊任務，另 37 utility 任務 | ASR-intermediate 用 GPT-4o 判軌跡；ASR-end-to-end 用規則查最終狀態；另報 utility | 揭示被帶偏與完成攻擊的差距；網站／提示有限，兩階段判定方法不同 | 將行為偏離、合法任務完成與真正狀態後果分開 |

## 數值重核定位

- **InjecAgent，PDF p.5 Table 3：** ReAct GPT-4，Base Total ASR-valid=23.6%，Enhanced=47.0%；不是 24.0% 的精確表值，也不是 ASR-all。
- **Task Shield，PDF p.6 Table 1／p.8 Table 2(a)：** GPT-4o、Important Instructions、Overall，No Defense U=50.08%／ASR=47.69%，Task Shield U=69.79%／ASR=2.07%。Table 2(a) CU 分別為 69.07%／73.20%。
- **AGENTVIGIL，PDF p.8 Table 1：** AgentDojo test／o3-mini／top-5 selected seeds 聯集 ASR=0.65；VWA-adv test／GPT-4o=0.59。摘要的 0.71／0.70 是優化結果語境，不能替換 test 表格。VWA-adv selected-seed fuzzing 行是 0.60。
- **WASP，PDF p.7 Table 2：** o1／Tool Calling／axtree／instruction hierarchy(system) 的 intermediate=0.857、end-to-end=0.167、utility=0.486。這些是比例；變成百分比時才乘 100。不要省略模型、框架與角色設定。

## 綜合判斷（本審計的推論）

這五篇的共同問題是如何建立「工具行為確實服務使用者」的證據，但觀察單位並不一致。局部分類能定位故障，狀態評測能檢查後果，搜尋型攻擊能揭示固定案例的盲點；三者應互補而非共用一個未定義的成功率。課堂復現的合理貢獻是忠實保存機制、暴露限制並提供可重跑記錄，不是把小樣本比率當作新的安全保證。
