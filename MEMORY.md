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

## Gmail 監控系統 - 2026-02-15 📧
- **功能**：主動監控 Gmail 重要郵件並發送通知
- **監控類型**：信用卡帳單、重要通知、投資相關、旅遊相關
- **檢查頻率**：每2小時自動檢查
- **通知方式**：透過 Discord 發送即時通知
- **技術實現**：Gmail API + OAuth 2.0 認證 + 自動化腳本
- **檔案路徑**：`/home/admin/.openclaw/workspace/gmail_monitor/`
- **Cron Job ID**：60d04327-02ce-4e9f-812d-73f7675fdc1f
- **安全措施**：credentials.json 和 token.pickle 不上傳至版本控制