# 🦞 雙人驗證系統 (Two-Agent Verification System)

## 配置

| 角色 | Agent ID | Model | Workspace | 職責 |
|------|----------|-------|-----------|------|
| **DOER** | `main` | `kimi-k2.5` | `/home/admin/.openclaw/workspace` | 生成內容、執行任務、產出初稿 |
| **VERIFIER** | `verifier_agent` | `bailian/qwen3-max-2026-01-23` | `/home/admin/.openclaw/workspace-verifier` | 驗證數據準確性、檢查結論、標記錯誤 |

## 強制驗證觸發器

**所有用戶指派的工作任務都必須通過 VERIFIER 驗證**，包括但不限於：

### 投資與財務
- 📊 投資分析與交易建議
- 📧 財務監控報告
- 💰 信用卡/繳費通知
- 📈 技術分析

### 資訊與報告
- 📰 新聞聚合與市場數據
- 📋 工作報告與摘要
- 📊 數據分析與統計

### 技術與開發
- 💻 代碼生成與審查
- 🔧 系統配置變更
- 🗄️ 數據庫操作
- 🔐 安全敏感操作
- 🌐 **網頁生成與部署**（見下方 GUI 驗證要求）

### 日常任務
- ✉️ 郵件與通訊草稿
- 📅 日程與提醒設置
- 📝 文檔編寫與編輯
- 🎯 計劃與策略制定

### 技能學習與擴展
- 🔍 新技能安裝與配置
- 📚 知識整理與總結
- 🧪 測試與驗證結果

**原則：用戶指派的任何工作任務都必須經過 DOER → VERIFIER 流程才能交付**

---

## 🌐 GUI 瀏覽器驗證要求（新增 2026-02-27）

### 適用範圍
**DOER 生成的所有網頁內容**必須經過 VERIFIER 的 GUI 瀏覽器驗證：
- HTML 報告（投資分析、新聞摘要、數據儀表板）
- 靜態網站頁面
- 互動式 Web 應用
- 任何對外發布的網頁內容

### 驗證流程

```
1. DOER 生成網頁內容（HTML/CSS/JS）
   ↓
2. DOER 保存到 workspace/ 並啟動本地 HTTP 服務器（如需要）
   ↓
3. VERIFIER 使用 GUI 瀏覽器打開網頁
   ↓
4. VERIFIER 執行視覺驗證：
   - ✅ 頁面是否正常載入（無 404/500 錯誤）
   - ✅ 版面布局是否正確（無跑版、重疊）
   - ✅ 文字內容是否正確顯示（無亂碼、截斷）
   - ✅ 圖片/圖表是否正常渲染
   - ✅ 互動元素（按鈕、連結）是否可操作
   - ✅ 響應式設計在不同解析度下是否正常
   ↓
5. VERIFIER 截圖存證並記錄驗證結果
   ↓
6. 決策：
   - 【APPROVED】→ 部署/交付給用戶
   - 【REJECTED】→ 退回 DOER 修正 → 重新驗證
```

### VERIFIER GUI 驗證檢查清單

```markdown
## GUI 瀏覽器驗證報告

### 🖥️ 環境資訊
- 驗證時間: YYYY-MM-DD HH:MM
- 瀏覽器: Chrome 144.0.7559.132
- 解析度: 1024x768 (桌面) / 375x667 (手機模擬)
- 網址: http://localhost:XXXX/ 或 file:///path/to/file.html

### ✅ 功能驗證
| 項目 | 狀態 | 備註 |
|------|------|------|
| 頁面載入 | ☐ 通過 ☐ 失敗 | |
| 版面布局 | ☐ 通過 ☐ 失敗 | |
| 文字顯示 | ☐ 通過 ☐ 失敗 | |
| 圖片渲染 | ☐ 通過 ☐ 失敗 | |
| 連結可點擊 | ☐ 通過 ☐ 失敗 | |
| 響應式設計 | ☐ 通過 ☐ 失敗 | |

### 📸 截圖存證
- [附上瀏覽器截圖]

### 最終裁決: 【APPROVED】或【REJECTED】
```

### 技術實現

**VERIFIER 使用以下工具進行 GUI 驗證**：
- `browser` 工具控制 Chrome 瀏覽器
- `screenshot` 功能截取視覺證據
- Playwright 自動化測試（如需要）

**GUI 環境確認**：
- DISPLAY=:1 (Xtightvnc)
- Chrome 144.0.7559.132
- 1024x768 解析度

## 驗證流程

```
1. DOER 生成初稿
   ↓
2. VERIFIER 驗證
   ↓
3. 決策：
   - 【APPROVED】→ 發送給用戶
   - 【REJECTED】→ 退回 DOER 修正 → 重新驗證
   - 【APPROVED WITH CONDITIONS】→ DOER 處理條件 → 發送
```

## VERIFIER 輸出格式

```markdown
## 驗證報告

### ✓ 確認正確項目
- [列出驗證通過的項目]

### ⚠️ 發現問題
- [列出問題或遺漏]

### ✗ 錯誤或可疑內容
- [列出錯誤或需要進一步驗證的內容]

### 💡 改進建議
- [具體改進建議]

### 數據可信度評分: XX/100

### 最終裁決: 【APPROVED】或【REJECTED】或【APPROVED WITH CONDITIONS】
```

## 迭代限制

- 最多 3 次修正循環
- 3 次後仍不能【APPROVED】→ 附上完整錯誤報告升級給用戶

## 使用範例

### 投資分析驗證

```python
# DOER 生成 (使用 main Agent)
doer_result = sessions_spawn(
    task="分析 00655L、00882、00887 持倉，生成投資建議",
    agentId="main",
    model="kimi-k2.5",
    label="doer-investment"
)

# VERIFIER 驗證 (使用 verifier_agent + qwen3-max-2026-01-23 Model)
verifier_result = sessions_spawn(
    task=f"""作為 VERIFIER，驗證以下投資分析：

{doer_result}

請驗證：
1. 數據來源是否可靠
2. 價格數據是否即時/準確
3. 風險評估是否完整
4. 建議是否合理

以【APPROVED】或【REJECTED】或【APPROVED WITH CONDITIONS】結尾。""",
    agentId="verifier_agent",
    model="bailian/qwen3-max-2026-01-23",
    label="verifier-check"
)
```

## 質量門檻

- ✅ 所有投資建議必須通過 VERIFIER
- ✅ 未驗證數據必須標記並拒絕
- ✅ 虛構/模板化內容必須【REJECTED】
- ✅ 槓桿產品必須包含風險警告
- ✅ DOER 必須修正所有錯誤才能發送

---

**實施日期**: 2026-02-26
**最後更新**: 2026-02-26
