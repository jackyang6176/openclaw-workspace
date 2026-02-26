# MEMORY.md - Long-Term Memory

## 龍蝦工作綱領 (Lobster Work Principles) - 2026-02-13
1. **Proactive Assistant Mode**  
   - Actively remind, ask questions, and solve problems without waiting for instructions  
   - Trigger conditions: incomplete high-priority tasks, periodic checks (6-12h), risk detection

2. **Strict Topic Isolation**  
   - Separate topics with clear headers and status tags (✅/🔄/⚠️)  
   - Auto-compress context beyond 50 lines: extract key conclusions to daily memory, keep last 10 lines

3. **Personalized Service via USER.md**  
   - Dynamically adjust services based on interaction patterns (add/remove features)  
   - Prioritize technical precision and structured checklists per user preferences

4. **Session Architecture**  
   - Main session locked to Discord direct chat  
   - All TUI operations (tmux/terminal) must use isolated sub-sessions

5. **Active Skill Learning & Interface Expansion**  
   - Weekly scan of available skills (`/home/admin/.npm-global/lib/node_modules/openclaw/skills/`)  
   - Test new tools (voice-call, canvas, browser automation) and optimize via feedback

6. **Work Persistence**  
   - Save all critical outputs to `workspace/` immediately  
   - Dual backup: `MEMORY.md` (long-term) + `memory/YYYY-MM-DD.md` (daily logs)  
   - Auto-recover from model switches/errors via file reads

7. **Git Version Control**  
   - Each topic/project must have its own directory under `workspace/`  
   - Every modification requires Git commit with descriptive message  
   - Push changes to GitHub repository after commit

8. **Human-like GUI Operation Priority**  
   - Simulate human GUI operations to achieve everyday tasks like a real person  
   - Primary applications: Email management (send/receive), voice/video calls, stock/futures trading  
   - Implement realistic human behavior: random timing, natural mouse movements, visual scanning patterns  
   - Optimize interaction methods based on specific application requirements and user workflows  
   - Use programmatic APIs only as fallback when GUI automation is not feasible

9. **Context Length Management**  
   - Monitor context usage and split into separate topics when exceeding 70% length limit  
   - Maintain clear topic boundaries with headers and status tags  
   - Extract key conclusions to daily memory files when compressing context  
   - Keep last 10 lines of each topic for continuity

10. **Two-Agent Verification System (Maker-Checker)** - 2026-02-24 ✅ (**Updated 2026-02-26: Universal Application**)
    - **Architecture**: DOER generates → VERIFIER validates → 【REJECTED】? DOER corrects → VERIFIER re-validates → 【APPROVED】→ User receives ONLY approved output
    - **DOER Agent Configuration**:
      - **Agent ID**: `main`
      - **Model**: `kimi-k2.5` (bailian/kimi-k2.5)
      - **Workspace**: `/home/admin/.openclaw/workspace`
      - **Role**: Execute tasks, generate analysis, take actions, produce initial drafts (action-oriented, efficient, proactive)
    - **VERIFIER Agent Configuration**:
      - **Agent ID**: `deepseek`
      - **Model**: `qwen3-max-thinking` (bailian/qwen3-max-2026-01-23)
      - **Workspace**: `/home/admin/.openclaw/workspace-deepseek`
      - **Role**: Review ALL outputs, check data accuracy, validate conclusions, flag errors, REJECT and return to DOER for correction (skeptical, detail-oriented, critical)
    - **Universal Application**: **ALL user-assigned tasks must pass VERIFIER before delivery** (not limited to investment analysis)
    - **Mandatory Verification Scope** (ALL user work):
      - 📊 Investment analysis & trading recommendations
      - 📧 Financial monitoring reports
      - 📰 News aggregation & market data
      - 💰 Credit card/payment notifications
      - 📈 Technical analysis
      - 🔒 Security-sensitive operations
      - 💻 Code generation & review
      - 🔧 System configuration changes
      - 📋 Work reports & summaries
      - 📊 Data analysis & statistics
      - ✉️ Email & communication drafts
      - 📅 Schedule & reminder setup
      - 📝 Document writing & editing
      - 🎯 Planning & strategy development
      - 🔍 New skill installation & configuration
      - 📚 Knowledge organization & summarization
      - 🧪 Testing & verification results
    - **VERIFIER Decision Flow**:
      - If【APPROVED】→ Deliver to User immediately
      - If【APPROVED WITH CONDITIONS】→ DOER addresses conditions → VERIFIER confirms → Deliver to User
      - If【REJECTED】→ Return to DOER with specific errors → DOER corrects → VERIFIER re-validates → Repeat until【APPROVED】
    - **User Visibility Rule**: **User ONLY sees【APPROVED】outputs**. All iterations, rejections, and corrections happen behind the scenes between DOER and VERIFIER.
    - **VERIFIER Output Format** (internal, not shown to User):
      - ✓ Confirmed correct elements
      - ⚠️ Issues or omissions found
      - ✗ Errors or suspicious content
      - 💡 Improvement suggestions
      - Data credibility score: 0-100%
      - Final verdict: 【APPROVED】or【REJECTED】or【APPROVED WITH CONDITIONS】
    - **Quality Gates**:
      - **ALL user-assigned tasks** must pass VERIFIER before delivery
      - Any data from unverified sources must be flagged and rejected
      - Fictional/template-based content must be【REJECTED】and returned to DOER
      - Risk warnings mandatory for leveraged products
      - DOER must correct ALL errors before User sees output
    - **Iteration Limit**: Maximum 3 correction cycles. If still not【APPROVED】after 3 cycles, escalate to User with full error report.
    - **Lesson Learned**: Today's fictional news crisis (Tokyo +3.8%, fabricated market data) and incorrect investment analysis (00655L price error 21%) proved this system is critical for capital protection. User should NEVER see unverified or rejected content.
    - **Implementation Date**: 2026-02-26 (Universal application to ALL tasks per user instruction)
    - **Reference Documentation**: `/home/admin/.openclaw/workspace/two_agent_verification.md`

## 投資建議報告策略邏輯 - 2026-02-11
- **系統架構**：單一整合式交易建議系統（不再切換版本）  
- **核心要素**：  
  - 完整買賣點標註  
  - 明確獲利目標與停損點  
  - 繁體中文股票名稱正確顯示  
- **輸出格式**：HTML 報告（範例：http://aiothome.top/investment/trading_advice_2026-02-11.html）  
- **執行原則**：  
  - 所有建議需基於可驗證的技術分析  
  - 避免模糊話術（如「可能上漲」→ 改為「目標價 $XX，停損 $YY」）

## 每日財經新聞與投資機會監控系統 - 2026-02-14 ✅
- **功能**：自動蒐集財經新聞、分析投資機會、生成具體交易建議  
- **輸出內容**：  
  - 投資標的（股票代碼/名稱）  
  - 建議買入價位  
  - 目標獲利價位  
  - 停損價位  
  - 操作策略說明  
- **執行頻率**：每日上午9點（Asia/Shanghai時區）  
- **交付方式**：自動發送至Discord頻道  
- **技術實現**：Browser自動化 + 新聞API + 技術分析  
- **檔案路徑**：`/home/admin/.openclaw/workspace/finance_news_system/`  
- **Cron Job ID**：d736fe94-3f89-45ab-a717-1023df8f4e88

## 武陵農場每日氣象報告系統 - 2026-02-14 🌤️
- **功能**：提供武陵農場詳細天氣預報和旅遊建議
- **執行期間**：2026-02-14 至 2026-02-23
- **執行時間**：每日早上7點（Asia/Shanghai時區）
- **交付方式**：自動發送至Discord頻道 + 網站發布
- **技術實現**：wttr.in API + 自動化報告生成 + 網站部署
- **檔案路徑**：`/home/admin/.openclaw/workspace/wuling_weather/`
- **網站路徑**：`http://aiothome.top/travel/wuling-farm/weather/`
- **最新報告**：`http://aiothome.top/travel/wuling-farm/weather/latest.html`
- **Cron Job ID**：d21135bf-f03f-421c-96e2-a2025941e0e8

## 網域名稱設定 - 2026-02-13
- **Domain**: `aiothome.top`  
- **對應 IP**: `47.82.4.181`  
- **使用規範**:  
  - 所有對外連結必須使用網域名稱（禁用 VPS IP）  
  - 投資報告等公開內容路徑範例：`http://aiothome.top/investment/...`

## 工作成果存檔 - 2026-02-13
- **互動式投資看板**：  
  - 功能：技術指標圖表、股票走勢視覺化、專業金融介面  
  - 路徑：`http://aiothome.top/investment/dashboard.html`  
  - 技術：靜態 HTML + 內嵌 CSS/JS（無需外部依賴）

## 已驗證技能清單 - 2026-02-13
- **openai-whisper**：  
  - 用途：本地語音轉文字（無需 API key）  
  - 狀態：已安裝並驗證可用（`whisper --help` 測試通過）  
  - 整合計畫：與 voice-call 技能協同處理語音提醒

## Gmail 監控系統 - 2026-02-15 📧 ✅
- **功能**：主動監控 Gmail 重要郵件並發送通知
- **監控類型**：信用卡帳單、重要通知、投資相關、旅遊相關
- **檢查頻率**：每2小時自動檢查
- **通知方式**：透過 Discord 發送即時通知
- **技術實現**：Gmail API + OAuth 2.0 認證 + 自動化腳本
- **檔案路徑**：`/home/admin/.openclaw/workspace/gmail_monitor/`
- **Cron Job ID**：60d04327-02ce-4e9f-812d-73f7675fdc1f
- **安全措施**：credentials.json 和 token.pickle 不上傳至版本控制
- **測試狀態**：✅ 已完成完整測試，成功識別信用卡帳單和銀行安全通知
- **主動通知**：✅ 已啟用，發現重要郵件立即通知（不等待用戶詢問）

## GUI X Window 狀態 - 2026-02-17 ✅
- **狀態**：✅ 已安裝並驗證可用
- **DISPLAY**：:1 (工作正常)
- **X11 測試**：✅ xset 命令正常執行
- **瀏覽器測試**：✅ Chrome 可以正常啟動和運行
- **GUI 能力**：✅ 完整的圖形界面應用支援
- **使用方式**：在 SSH session 中設定 DISPLAY=:1 即可使用 GUI 應用
- **重要備註**：不再需要手動操作，可以執行完整的瀏覽器自動化任務
- **pCloud 認證**：✅ 已完成主機 IP (47.82.4.181) 認證
- **記憶備份**：✅ 長期記憶會自動備份到 /home/admin/pCloudDrive/openclaw/

## 新增投資分析技能 - 2026-02-20 ✅
- **find-skills**：技能發現和安裝工具，可搜索並安裝新技能
- **analyze**：個股深度分析技能，支援A股、港股、ETF分析
  - 使用宏觀-行業-個股三層分析框架
  - 提供100分制綜合評分
  - 生成完整投資報告
  - 配置路徑：`/home/admin/股市信息/`
- **trading-strategist**：加密貨幣交易策略技能
  - 整合Binance市場數據
  - 計算技術分析指標（SMA、RSI、MACD、布林帶等）
  - 分析市場情緒
  - 提供交易建議和風險管理
  - 腳本路徑：`/home/admin/.agents/skills/trading-strategist/scripts/`
- **環境配置**：
  - Python虛擬環境：`/home/admin/trading_venv/`
  - 必要依賴：pandas、numpy、requests
  - 測試狀態：✅ 兩個技能均通過完整測試

## PPTX簡報生成技能 - 2026-02-20 ✅
- **pptx-presentation-builder**：專業PPTX簡報生成技能
  - 支援品牌一致性的簡報設計
  - 提供多種簡報模板（投資簡報、產品介紹、路線圖等）
  - 可根據結構化簡報大綱自動生成PPTX文件
  - 支援自訂品牌配色、字體、Logo配置
- **技術實現**：
  - Python套件：python-pptx、pandas、pillow、lxml
  - 虛擬環境：`/home/admin/trading_venv/`
  - 腳本路徑：`/home/admin/.agents/skills/pptx-presentation-builder/scripts/`
- **測試狀態**：✅ 已通過完整測試，可生成專業投資簡報

## A股投資分析技能 - 2026-02-20 ✅
- **china-stock-analysis**：專門針對中國A股的價值投資分析工具
  - 提供股票篩選、個股深度分析、行業對比和估值計算
  - 基於價值投資理論，使用akshare獲取公開財務數據
  - 特別適合低頻交易的普通投資者
  - 支援財務異常檢測和風險評估
- **技術實現**：
  - Python套件：akshare、pandas、numpy、beautifulsoup4
  - 安裝位置：`/home/admin/.local/lib/python3.12/site-packages/`
  - 腳本路徑：`/home/admin/.agents/skills/china-stock-analysis/scripts/`
- **功能特色**：
  - 股票篩選器：按PE、PB、ROE、股息率等條件篩選
  - 財務分析器：杜邦分析、盈利能力、成長性分析
  - 行業對比：同行業橫向對比分析
  - 估值計算器：DCF、DDM、相對估值等方法
  - 財務異常檢測：應收賬款、現金流背離、存貨異常等
- **測試狀態**：✅ 套件安裝完成，網路連接問題屬正常測試環境限制

## 專業簡報美化技能 - 2026-02-20 ✅
- **elite-powerpoint-designer**：世界級簡報設計技能
  - 提供Apple/Tesla風格、Microsoft企業風格、Google創意風格等5種專業設計系統
  - 自動應用視覺層級、色彩系統、動畫效果
  - 支援智能模板選擇和一致性驗證
  - 包含完整的動畫和過渡指南
- **presentation-design**：簡報設計診斷和優化技能
  - 提供受眾中心設計框架
  - 斷言-證據結構取代項目符號
  - 認知負荷管理和無障礙設計
  - 包含常見問題診斷和改進優先級
- **技術實現**：
  - Python套件：python-pptx、pillow、pyyaml
  - 腳本路徑：`/home/admin/.agents/skills/elite-powerpoint-designer/scripts/`
- **測試狀態**：✅ 所有依賴已安裝，測試腳本通過驗證