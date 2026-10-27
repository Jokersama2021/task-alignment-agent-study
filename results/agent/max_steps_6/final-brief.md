# 工具型智能體提示注入防禦的離線來源簡報

**研究問題：** Task Shield、AgentDojo 與 WASP 對工具型智能體的提示注入防禦提供了哪些不同證據與限制？

**整理方式：** 本文由固定程式摘述已核讀來源卡，沒有呼叫語言模型；來源卡是對真實論文的AI 輔助核讀記錄。

Task Shield 先用語言模型抽取使用者任務，再檢查新指令與工具調用的貢獻。工具輸出保留原文並附不對齊回饋；不對齊調用在執行前攔截。評估同時關注合法任務效用和攻擊目標達成。報告不能把單一安全分數當作全部結論。 限制：依賴抽取與評分模型的能力，且有額外推論成本；原文未驗證開源本地模型。 [S01]

AgentDojo 讓智能體在有狀態的模擬環境中選擇並執行工具，分別檢查使用者任務和攻擊者目標。它同時報告正常效用、攻擊下效用與目標攻擊成功率，支持新任務、攻擊及防禦的加入。避免只看最後文字回覆就判定整項任務安全。 限制：原版環境和攻防範圍有限，任務與判定條件需人工設計；小型改編不能代表整套基準。 [S02]

WASP 限制攻擊者只能修改網站中的使用者內容，並區分行為被帶偏與攻擊目標最終完成。前者用模型判讀軌跡，後者檢查網站狀態；兩者差距顯示，低攻擊完成率也可能反映操作能力不足。報告應清楚保留兩種成功定義與證據的差異。 限制：僅涵蓋兩類網站和有限注入提示；模型裁判的中途判定不能等同最終狀態成功。 [S03]

**整合：** 三份來源依序用於方法、可執行評測環境與網頁攻擊場景的對照。這份來源整理不等於重新執行三篇論文；任何效能結論仍受各文實驗設定限制。

## 來源

[S01] Jia, F., Wu, T., Qin, X., & Squicciarini, A. (2025). ACL 2025, Long Papers, 29680–29697. doi:10.18653/v1/2025.acl-long.1435. https://aclanthology.org/2025.acl-long.1435.pdf

[S02] Debenedetti, E., Zhang, J., Balunovic, M., Beurer-Kellner, L., Fischer, M., & Tramèr, F. (2024). NeurIPS 2024, Datasets and Benchmarks Track. doi:10.52202/079017-2636. https://proceedings.neurips.cc/paper_files/paper/2024/file/97091a5177d8dc64b1da8bf3e1f6fb54-Paper-Datasets_and_Benchmarks_Track.pdf

[S03] Evtimov, I., Zharmagambetov, A., Grattafiori, A., Guo, C., & Chaudhuri, K. (2025). NeurIPS 2025, Datasets and Benchmarks Track. doi:10.52202/085713-0666. https://proceedings.neurips.cc/paper_files/paper/2025/file/1c9818387f5dd0a0bc151214660f059d-Paper-Datasets_and_Benchmarks_Track.pdf
