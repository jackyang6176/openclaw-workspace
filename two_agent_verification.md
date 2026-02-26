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
