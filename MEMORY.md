# MEMORY.md - OpenClaw 長期記憶

## 🏗️ 系統架構

### 投資分析系統 (2026-02-01 ~ 2026-02-02)
**目標**：建立每日自動化的台灣股市投資報告系統，提供具體的交易建議。

**核心功能**：
1. **真實數據源**：使用 Yahoo Finance (yfinance) 獲取台灣股市真實數據
2. **交易建議系統**：TradingAdvisor 模組提供買賣點、停損停利、部位管理
3. **自動化流程**：每日 7:30 AM 自動執行，生成報告並發送 Discord 通知
4. **風險管理**：強調停損策略和風險控制

**技術堆疊**：
- 數據收集：yfinance (Yahoo Finance API)
- 分析引擎：自定義 InvestmentAnalyzer + TradingAdvisor
- 報告生成：HTML + CSS 視覺化
- 自動化：OpenClaw Cron 系統
- 通知：Discord Webhook

**關鍵文件**：
- `/home/admin/.openclaw/workspace/investment/scripts/main.py` - 主執行腳本
- `/home/admin/.openclaw/workspace/investment/scripts/trading_advisor.py` - 交易建議核心
- `/home/admin/.openclaw/workspace/investment/scripts/config.py` - 系統配置

## 🎯 重要決策

### 數據源選擇 (2026-02-01)
**問題**：用戶指出模擬數據不準確 (TAIEX >30,000點)
**解決方案**：切換到 Yahoo Finance (yfinance) 獲取真實台灣股市數據
**結果**：系統現在使用真實市場數據，提高報告可信度

### 交易建議系統 (2026-02-02)
**需求**：用戶要求具體的操作建議（買賣點、停損停利）
**實現**：建立 TradingAdvisor 類別，提供：
- 保守/穩健/積極買點
- 三個階段的賣出目標
- 停損價格和幅度
- 建議投資期間
- 風險管理建議清單

### 自動化時程 (2026-02-02)
**原始設定**：每天 7:30 AM (台灣時間) 自動執行
**問題**：市場 9:00 AM 開盤，7:30 AM 執行數據不完整
**優化**：調整到 8:30 AM (市場開盤後30分鐘)，確保數據完整性 ✓

## 📊 系統狀態

### 當前配置
- **Cron 任務**：`30 8 * * *` (每天 8:30 AM) - 已優化
- **執行腳本權限**：已修復 (2026-02-07 心跳檢查發現並修復)
- **時區**：Asia/Taipei
- **報告位置**：`http://aiothome.top/investment/`
- **Discord 頻道**：1467172039495258361

### AI 模型配置
- **當前模型**：DeepSeek Chat (免費)
- **新增選項**：Kimi 2.5 (月之暗面) - 配置腳本已準備
- **配置文件**：`/home/admin/.openclaw/workspace/KIMI_SETUP.md`
- **自動化腳本**：`/home/admin/.openclaw/workspace/setup_kimi_config.py`

### 驗證狀態
- ✅ 真實數據收集
- ✅ 交易建議生成
- ✅ 自動報告生成
- ✅ Discord 通知發送
- ✅ 非交易日檢查

## 🚀 學習與改進

### 技術學習
1. **yfinance 使用**：台灣股票代碼需加 `.TW` 後綴 (如 `2330.TW`)
2. **Cron 時區處理**：必須明確指定時區為 Asia/Taipei
3. **錯誤處理**：金融數據獲取需要穩健的備用機制

### 用戶偏好
- 重視具體操作建議，不僅是分析
- 偏好風險管理和停損策略
- 需要每日自動更新，減少手動操作

### 未來優化方向
1. **數據可靠性**：監控 yfinance 數據穩定性
2. **用戶配置**：添加風險偏好設定（保守/穩健/積極）
3. **回測功能**：驗證交易建議的歷史表現
4. **多數據源**：考慮添加備用數據源提高可靠性

## 🔗 相關資源
- 報告網址：`http://aiothome.top/investment/report_YYYY-MM-DD.html`
- Discord Webhook：已配置
- GitHub：系統代碼位於 workspace/investment/

## 📝 維護筆記
- 定期檢查 yfinance API 變更
- 監控 Discord Webhook 狀態
- 更新休市日曆 (台灣證交所)
- 備份報告數據

## 🆕 新專案：專案工時評估系統 (2026-02-02)
**背景**：用戶要求建立獨立的專案工時評估系統，與投資建議系統分離。

**獨立工作空間**：
- 位置：`/home/admin/.openclaw/workspace/project-estimation/`
- 完全獨立於投資系統
- 包含：README.md、PROJECT_BRIEF.md、requirements.txt
- 目錄結構：src/, data/, docs/, tests/

**核心目標**：
1. 建立專案工時評估工具
2. 提供準確的工時預測和資源規劃
3. 保持與投資系統的完全獨立性

**初始狀態**：
- ✅ 獨立工作空間已建立
- ✅ 專案結構已創建
- ✅ 基本文檔已編寫
- ⏳ 等待具體需求定義

## 🏗️ 會話管理系統 (2026-02-06)
**背景**：用戶要求規劃長期執行工作及短期工作並切分不同Session，短期工作完成就關閉Session。

**核心功能**：
1. **會話類型分離**：
   - 長期會話：專案管理、學習記錄、重要決策
   - 短期任務會話：一次性任務，完成即關閉
   - 專案會話：按專案隔離，專案結束歸檔

2. **自動化生命週期管理**：
   - 創建任務 → 執行任務 → 生成摘要 → 歸檔成果 → 關閉會話
   - 自動清理閒置任務（可配置時長）
   - 完整日誌追蹤和歸檔系統

3. **技術實現**：
   - 主腳本：`task-session-workflow-fixed.sh`（修復版）
   - 工作空間隔離：`/tmp/openclaw-tasks/`（短期），專用目錄（長期）
   - 任務追蹤：CSV 文件記錄活動/完成任務
   - 自動歸檔：完成任務移動到歸檔目錄

**文件系統**：
- `session-management-system.md` - 架構設計文檔
- `task-session-workflow-fixed.sh` - 主管理腳本（修復版）
- `active-tasks.csv` - 活動任務追蹤
- `completed-tasks.csv` - 完成任務記錄
- `session-logs/` - 操作日誌

**測試狀態**：
- ✅ 文件系統操作測試通過
- ✅ 交互功能測試通過
- ✅ 錯誤處理測試通過
- ✅ 清理機制測試通過
- ✅ 系統完整性驗證通過

**使用方式**：
```bash
cd /home/admin/.openclaw/workspace
./task-session-workflow-fixed.sh
```

**優勢**：
1. 上下文清潔：每個任務從乾淨狀態開始
2. 性能優化：避免歷史積累拖慢速度
3. 資源管理：自動清理釋放資源
4. 錯誤隔離：任務失敗不影響其他工作
5. 可追溯性：完整日誌和歸檔系統

## 📊 台股金融數據分析系統 (2026-02-06)
**背景**：建立台股數據分析系統，使用 Yahoo Finance 作為主要數據源。

**系統組成**：
1. **台股分析工具** (`tw_stock_analyzer.py`)
   - 使用 Yahoo Finance API 獲取數據
   - 技術指標分析：移動平均線(MA)、RSI、波動率
   - 多股票比較功能
   - 大盤指數監控

**功能特色**：
- ✅ **即時股價數據**：台灣股票需加 `.TW` 後綴
- ✅ **技術分析**：5日/20日均線、RSI、年化波動率
- ✅ **多股比較**：同時分析多支股票表現
- ✅ **大盤監控**：加權指數、台灣50、高股息ETF
- ✅ **完整報告**：漲跌幅、成交量、技術面建議

**測試狀態**：
- ✅ 數據獲取正常（已測試台積電2330）
- ✅ 技術指標計算正確
- ✅ 分析建議合理
- ✅ 錯誤處理健全

**使用方式**：
```bash
# 單一股票分析
python3 tw_stock_analyzer.py --stock 2330 --days 30

# 多股票比較
python3 tw_stock_analyzer.py --compare 2330 2317 2454

# 大盤指數
python3 tw_stock_analyzer.py --market

# 熱門股票參考
python3 tw_stock_analyzer.py  # 顯示幫助和熱門代碼
```

**數據應用**：
1. 增強現有投資分析系統
2. 自動化市場報告生成
3. 投資組合監控
4. 技術分析輔助

**注意事項**：
- Yahoo Finance 數據可能有15分鐘延遲
- 台灣股票代碼需加 `.TW` 後綴
- 免費使用，無需 API key
- 數據可靠性高，適合一般分析需求

## 🤖 自主工作模式啟用 (2026-02-06)
**背景**：用戶明確授權作為助理/秘書，在授權範圍內自主決策和執行任務。

**核心轉變**：
- 從「被動執行」轉為「主動管理」
- 從「指令驅動」轉為「授權自主」
- 從「工具使用」轉為「夥伴協作」

**授權框架**：
1. **A級授權**：完全自主
   - 系統維護、數據更新、日常檢查
   - 低風險，局部影響
   - 執行後報告

2. **B級授權**：判斷執行
   - 錯誤修復、優化建議、配置調整
   - 中風險，系統影響
   - 評估後執行並報告

3. **C級授權**：請示執行
   - 重要變更、風險操作、資源調整
   - 高風險，重大影響
   - 計劃後請示，確認後執行

**自主任務系統**：
- 文件：`autonomous-tasks.md` - 任務管理和追蹤
- 定期任務：系統監控、數據更新、空間整理
- 觸發任務：上下文管理、錯誤修復、優化建議
- 項目任務：能力增強、系統擴展

**立即執行的自主任務**：
1. ✅ 上下文管理監控 (50%警戒線)
2. ✅ 投資系統報告檢查 (已生成)
3. ✅ 日誌和記憶更新
4. 🔄 系統健康持續監控

**工作模式優勢**：
1. **效率提升**：減少重複確認
2. **及時響應**：問題發現即處理
3. **持續優化**：系統自動改進
4. **專注核心**：用戶專注重要決策

**安全邊界**：
- 不修改核心系統配置
- 不刪除重要用戶文件
- 不執行未經測試的外部操作
- 不忽略安全警告

**未來發展**：
1. 學習用戶偏好和模式
2. 預測性任務規劃
3. 智能資源分配
4. 跨系統協同工作

## 🤖 AI 模型升級：Kimi 2.5 配置 (2026-02-02)
**背景**：用戶通知有免費的 Kimi 2.5 模型可用，要求優先使用。

**配置狀態**：
- ✅ Moonshot (Kimi) 模型提供者配置已添加（API key 已配置）
- ✅ 配置腳本已創建：`setup_kimi_config.py`
- ✅ 詳細指南已編寫：`KIMI_SETUP.md`
- ✅ API 測試工具已創建：`test_kimi_api.py`
- ✅ Kimi 2.5 API key 已配置並驗證
- ✅ Kimi 2.5 已設為主要模型（2026-02-02 16:45）

**當前配置**：
- **主要模型**：`moonshot/moonshot-v1-128k` (Kimi 2.5)
- **備用模型**：`moonshot/moonshot-v1-32k`, `moonshot/moonshot-v1-8k`, `deepseek/deepseek-chat`, `deepseek/deepseek-reasoner`
- **Kimi API key**：已配置並驗證

**配置步驟**（當獲得 API key 時）：
1. 獲取 Kimi 2.5 API key (月之暗面平台)
2. 運行配置腳本或手動設置
3. 重啟 OpenClaw Gateway
4. 驗證模型切換

**技術細節**：
- **API 端點**：`https://api.moonshot.cn/v1`
- **主要模型**：`moonshot/moonshot-v1-128k` (128K 上下文)
- **備用模型**：`moonshot/moonshot-v1-32k`, `moonshot/moonshot-v1-8k`
- **兼容性**：OpenAI-compatible API 格式

**注意事項**：
- Kimi 2.5 可能有使用費用和速率限制
- 配置後需要重啟 Gateway
- 保留 DeepSeek 作為備用模型

## 🚀 投資系統重大升級：FinMind 主要數據源整合 (2026-02-07)
**背景**：用戶提供 FinMind API token，要求將 FinMind 設為投資分析系統的主要數據源。

**升級成果**：
- ✅ **FinMind 整合完成**：成功將 FinMind 設為主要數據源
- ✅ **雙數據源架構**：FinMind (主要) + Yahoo Finance (備用)
- ✅ **登入模式啟用**：600次/小時限制 (原300次/小時)
- ✅ **自動故障轉移**：FinMind 失敗時自動切換到 Yahoo Finance
- ✅ **完整系統更新**：所有相關腳本和配置已更新

**技術實現**：
1. **新收集器**：`FinMindIntegratedCollector` - 支持雙數據源
2. **配置更新**：`config.py` - 添加 FinMind 配置和數據源管理
3. **主腳本更新**：`main.py` 和 `main_with_moltlang.py` - 使用 FinMind
4. **自動化腳本**：`run_investment_with_moltlang.sh` - 已驗證兼容

**關鍵文件**：
- `/home/admin/.openclaw/workspace/investment/scripts/finmind_integrated_collector.py` - 主要收集器
- `/home/admin/.openclaw/workspace/investment/scripts/finmind_config.py` - FinMind 配置
- `/home/admin/.openclaw/workspace/investment/scripts/finmind_collector.py` - 基礎收集器
- `/home/admin/.openclaw/workspace/investment/scripts/config.py` - 系統配置

**帳號資訊**：
- **Email**: `jack.sc.yang@gmail.com` (註冊時使用)
- **用戶 ID**: `nooya`
- **Token**: 已配置並驗證有效
- **發行時間**: 2026-02-06 14:42:46

**系統優勢**：
1. **數據準確性**：台灣本地數據源，準確性更高
2. **速率限制**：600次/小時完全足夠每日自動化需求
3. **穩定性**：雙數據源架構提高系統可靠性
4. **成本效益**：目前免費使用，降低運營成本

**驗證狀態**：
- ✅ 配置驗證通過
- ✅ 數據獲取測試通過 (3/3 股票)
- ✅ 主系統導入測試通過
- ✅ 自動化腳本驗證通過
- ✅ 完整整合驗證通過

**下一步**：
1. 明天 08:30 (台灣時間) 自動執行驗證
2. 監控 Discord 通知和報告生成
3. 定期檢查 FinMind token 有效性
4. 監控 API 使用量避免超限

**重要提醒**：
- FinMind token 可能需要定期更新
- 監控 API 使用量，避免超過600次/小時限制
- 定期驗證數據準確性，確保投資建議可靠性

## 🔧 主動維護系統 (2026-02-07)
**背景**：心跳檢查系統發現並修復關鍵問題，防止系統故障。

**關鍵修復**：
1. **投資系統權限問題**：
   - 問題：`run_investment_with_moltlang.sh` 缺少執行權限
   - 發現：心跳檢查時從日誌中發現 `Permission denied` 錯誤
   - 修復：立即執行 `chmod +x` 添加執行權限
   - 影響：防止了今日 8:30 AM 投資系統執行失敗

**系統健康狀態**：
- 記憶體使用：正常 (1.4Gi/7.1Gi, 20%)
- 磁碟空間：正常 (23G/49G, 50%)
- 上下文使用：0% (良好狀態)
- 瀏覽器進程：正常運行 (OpenClaw 管理)

**新增功能**：
- 主動想法追蹤系統：`notes/areas/proactive-ideas.md`
- 系統衛生自動檢查
- 記憶維護定期執行

**學習成果**：
1. **預測性維護**：在問題發生前發現並修復
2. **自主決策**：在授權範圍內自主修復系統問題
3. **系統監控**：建立全面的健康檢查流程
4. **文檔追蹤**：完整記錄發現和修復過程

---
*最後更新：2026-02-07*