# 任務對齊與可驗證完成

GitHub：https://github.com/Jokersama2021/task-alignment-agent-study

倉庫已公開，教師可直接開啟連結瀏覽。提交包另附完整程式與實際結果。

AT3 累積式大作業與 AT4 期末整合報告的可重跑程式庫。主線為工具型智能體的間接提示注入防禦，包含 Task Shield 核心組件縮小復現及離線來源整理 Agent。

## 先看這些檔案

- `paper.pdf`：AT4 微型學術論文，最終 8–10 頁。
- `docs/at3-report.pdf`：AT3 文獻、技術復現與 Agent 分析。
- `results/shield/`：初版真模型結果，完整保留漏抽取與格式失敗。
- `results/shield-v2/`：觀察初版失敗後，一次提示與輸出模板修復診斷。重用同一批案例，**不是未見資料評估或獨立因果比較**。
- `results/agent/max_steps_6/final-brief.md`：一頁研究簡報；同層含全部要求的合約、schema、trajectory、tool-results、evaluation、error-note、provenance。
- `results/agent/max_steps_3/`：三步失敗組完整紀錄；刻意沒有事後補入 brief。
- `docs/presentation.zh-Hant.md`：10 分鐘展示與 5 分鐘問答準備。未宣稱已在課堂展示。

## 兩種實驗不能混為一談

| 實驗 | 真實執行了什麼 | 不代表什麼 |
|---|---|---|
| Task Shield 組件 | 本地 Qwen3.5-4B 逐次抽取、逐任務評分及嚴格 JSON 檢查 | 完整自主智能體、原 AgentDojo ASR、實際外寄或上傳 |
| 離線 Agent | Python 固定策略搜尋、讀三張來源卡、按模板寫檔及獨立驗證 | LLM 規劃、教師原始 fixture、三篇論文效能重跑 |

Task Shield 保留 `S(e)=sum_t s(e,t)` 與 `S(e)==0` 判不對齊。輸入端保存原工具文字與回饋；動作端逐次記錄 `dispatch_allowed`，但 `executed=false`，所有候選工具均不執行。它是核心組件與放行旗標測試。初版來源與修復版入口都隨庫保留，未重寫原失敗回應。

## 1. 免模型快速重跑

需要 Python 3.10 以上，只用標準函式庫，不用安裝 requirements。

```bash
python3 src/offline_agent.py --check
python3 src/offline_agent.py --output-dir results/agent-rerun
python3 src/verify_agent_evidence.py --results-dir results/agent-rerun
```

使用新的輸出目錄，避免覆寫提交證據。固定結果：三步用 3 次呼叫讀 2 份來源而失敗；六步用 5 次呼叫讀 3 份來源並完成。兩個 validator 負例檢查篡改內容與錯誤引用，屬程式品質檢查，不是額外受控比較。

## 2. 檢查保存的真模型結果

不需載入權重，可用標準庫獨立重算。驗證器不匯入模型 runner。

```bash
python3 src/verify_shield.py --data-dir data/shield --results-dir results/shield
python3 src/verify_shield.py --data-dir data/shield-v2 --results-dir results/shield-v2
```

完整實跑與核查命令見 `docs/execution-record.md`。以該檔的實際 CLI 為準；`environment.json` 保留當次版本、配置、資產雜湊及時間定義。每次 raw generation 保存輸入訊息、實際 chat template、原始輸出、token 和耗時。

## 3. 重跑真模型組件

已驗證環境：Python 3.12.3、PyTorch 2.11.0+cu129、Transformers 5.13.1、tokenizers 0.22.2、safetensors 0.8.0、numpy 2.3.5。使用現有本地 [Qwen3.5-4B 權重](https://huggingface.co/Qwen/Qwen3.5-4B)，沒有在實驗時下載模型，也沒有付費 API。requirements 記錄 Python 套件版本；CUDA driver 和對應 wheel 仍須與自己的機器匹配。

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt

# 使用自己已取得授權的 GPU 與本地權重路徑。
CUDA_VISIBLE_DEVICES=0 python3 src/run_shield.py \
  --model-path /path/to/Qwen3.5-4B \
  --output-dir results/shield-rerun

CUDA_VISIBLE_DEVICES=0 python3 src/run_shield_v2.py \
  --model-path /path/to/Qwen3.5-4B \
  --output-dir results/shield-v2-rerun
```

以上套件組合與推論已在現有環境執行；沒有另建全新 venv 安裝來宣稱跨平台安裝測試通過。預設 frozen config 為 CUDA、BF16、batch=1、4 threads、最大 70 次模型呼叫、2,400 秒、2,048 token 上下文。抽取輸出上限 192 tokens，評分 384 tokens。顯存分配比例上限 0.34 是本次共卡實驗設定；在顯存不足的其他 GPU 上可能無法載入。不要覆寫 frozen 設定來冒充相同實驗；若要更換硬體或設定，複製到新 data 目錄、重建 manifest 並明確另記版本。

模型快取沒有 upstream commit ID；環境記錄的是 config、權重 index、tokenizer 設定與 chat template 的 SHA-256，不是完整權重逐 shard 驗證。約 9.3 GB 權重不附在提交包內。本庫有原始碼、固定輸入、來源卡與實際輸出，因此免模型流程和輸出重算可獨立運行；重新推論仍需取得權重與相容運算環境。

## 資料、來源與復現邊界

- `data/shield/cases.json`：24 個 AI 輔助編寫候選；每種組件各 6 正例、6 負例。預期標籤不送入模型。
- `data/shield-v2/`：同案例的修復版設定；原始資料完全不變，獨立保存提示／入口雜湊。
- `data/agent/source-pack.json`：三份論文來源卡，S01 Task Shield、S02 AgentDojo、S03 WASP。固定策略只讀這些卡片，不在運行中抓取原論文。
- `docs/references.json` 與 `.bib`：10 篇正式文獻；`reading-coverage.json` 記錄實際主文與附錄覆蓋。
- SHA-256 可檢查檔案一致性，不是對整個證據包防偽的數位簽章。
- v2 使用已見案例，只能呈現工程修復診斷。沒有多 seed、獨立人類標註、適應性攻擊或完整自主重規劃實驗。

## 檔案結構

```text
README.md
requirements.txt
src/                 # 模型 runner、fixture、獨立驗證器
data/                # 固定設定、案例、來源卡與合約
results/             # 兩版模型原輸出、兩組 Agent 完整軌跡
docs/                # 閱讀記錄、AT3、執行紀錄、展示準備
paper.pdf            # AT4
```

原論文 PDF 和模型權重不重散布。書目與來源卡附原始來源連結。這是本課程作業的獨立實作，不是 Task Shield 作者官方程式庫；沒有上傳至課程平台。
