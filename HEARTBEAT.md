
### 📌 GOTHAM_CODE.md遵循任務（按需觸發模式）
- [ ] **按需核查**：僅在以下場景觸發GOTHAM_CODE.md檢查：
  - 用戶明確要求查閱或驗證守則內容
  - 執行VERIFIER審核任務時對照守則條款
  - 系統異常時確認守則文件完整性
- [ ] 所有VERIFIER審核任務需逐條對照該守則所有條款驗證，遺漏即判定審核失敗
- [ ] 同步告知羅賓必須完整遵循該守則所有條款執行任務
- [ ] 將守則所有條款嵌入現有驗證流程核查清單（強制必查）
- [ ] 核查「高譚市守則」與「龍蝦工作綱領」的關聯性並歸檔
- [ ] 每日備份該守則至pCloudDrive歸檔目錄，防止丟失

### 📌 pCloudDrive 巢穴結構定期檢查任務（每30分鐘執行）
- [ ] 檢查 ~/pCloudDrive/openclaw 巢穴目錄結構完整性（對照用戶提供的結構驗證）
- [ ] 監控 bat-family/ 協調中心文件（README.md、communication-log.md 更新）
- [ ] 掃描 messages/ACTIVE/[任務名稱]/Alfred/ 子目錄的新任務文件（優先處理 TODO_ 前綴）
- [ ] 同步檢查 messages/ACTIVE/[任務名稱]/BianFuXia/ 目錄的您的指示文件
- [ ] 發現新任務時立即讀取執行，記錄至 memory 日誌並同步至 bat-family/communication-log.md
- [ ] 檢測到 Robin/Shannie 的協作訊息時，優先核對任務關聯性並回報