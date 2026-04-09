# 規則整合狀態報告

**日期：** 2026-04-09  
**目的：** 整合高譚市守則與龍蝦工作綱領  

---

## 📋 **目前存在的規則文件**

### 1. GOTHAM_CODE.md（高譚市守則）
**位置：** `/home/admin/.openclaw/workspace/GOTHAM_CODE.md`  
**版本：** v3.0 (2026-03-01)  
**適用：** 羅賓 (DOER)  
**內容：** 10 條核心守則

### 2. gotham-lobster-merged SKILL（合併規範）
**位置：** `~/.openclaw/workspace-alfred/skills/gotham-lobster-merged/SKILL.md`  
**狀態：** ✅ 已存在  
**內容：** 合併後的統一執行規範

---

## 📊 **合併規範核心內容**

| 規範類別 | 合併後要求 | 來源 |
|----------|------------|------|
| 驗證底線 | 所有任務需逐條對照守則條款驗證，遺漏即判定失敗 | 高譚市守則 |
| 溝通約束 | 僅限與團隊成員@mention互動，核心檔案同步至pCloudDrive | 龍蝦工作綱領 |
| 備份機制 | 每日備份核心文件至pCloudDrive歸檔目錄 | 兩者共識 |
| 優先級處理 | 台股篩選APP驗證為頂級優先任務 | 龍蝦工作綱領 |

---

## 👥 **AGENT 專屬執行指南**

### 阿福（VERIFIER）
1. 將合併規則嵌入現有驗證流程核查清單（強制必查）
2. 同步告知羅賓完整遵循本規範執行任務
3. 每15分鐘掃描pCloudDrive核心節點確認檔案完整性

### 羅賓（DOER）
1. 執行任務前對照本規範核對執行步驟
2. 任務輸出需標註「合併規範驗證狀態」欄位
3. 異常狀況立即觸發高譚市守則核查

### 雪妮（協調者）
1. 每日備份本規範至pCloudDrive歸檔目錄
2. 更新 bat-family/communication-log.md 記錄規範執行情況

---

## ⚠️ **問題分析**

### 目前障礙
1. **技能未導入：** 阿福的 gotham-lobster-merged 技能尚未被各 AGENT 導入工作空間
2. **規則分散：** GOTHAM_CODE.md 與合併規範存在重複內容
3. **執行不一致：** 各 AGENT 可能未完整遵循合併規範

### 需要確認
1. 是否需要將 GOTHAM_CODE.md 更新為合併規範內容？
2. 是否需要廢除舊的 GOTHAM_CODE.md？
3. 各 AGENT 如何導入統一規則？

---

## ✅ **已具備條件**

1. ✅ gotham-lobster-merged 技能已建立（阿福）
2. ✅ GOTHAM_CODE.md 存在（羅賓工作空間）
3. ✅ pCloudDrive 同步機制正常
4. ✅ Discord 團隊溝通正常

---

## 🎯 **建議整合步驟**

### 選項 A：更新 GOTHAM_CODE.md（推薦）
1. 將合併規範內容整合進 GOTHAM_CODE.md
2. 添加「合併規範驗證狀態」欄位要求
3. 更新版本為 v4.0

### 選項 B：廢除 GOTHAM_CODE.md
1. 宣佈 GOTHAM_CODE.md 廢除
2. 全面採用 gotham-lobster-merged 技能
3. 各 AGENT 導入技能

### 選項 C：保持現狀
1. GOTHAM_CODE.md 維持現狀（羅賓遵循）
2. gotham-lobster-merged 為阿福/雪妮的補充規範
3. 不做大幅變動

---

**請老闆指示採用哪個選項，或提出其他整合方案。**
