# 系統資源監控整合指南

## 📋 概述

已將內存、硬碟、CPU 等系統資源監控整合到統一的監控系統中。

**執行時間**: 2026-02-28 11:47 AM  
**整合項目**: 內存 + 硬碟 + CPU + Chrome 進程  
**監控頻率**: 每小時自動檢查  
**警報閾值**: 可配置

---

## 🎯 監控腳本

### 1️⃣ system_monitor.sh - 自動監控腳本

**路徑**: `/home/admin/.openclaw/workspace/scripts/system_monitor.sh`

**功能**:
- 每小時自動執行
- 監控內存、Swap、硬碟、Chrome 進程
- 超過閾值時發送 Discord 警報
- 記錄到日誌文件

**監控指標**:
| 指標 | 警告閾值 | 嚴重閾值 |
|------|---------|---------|
| **內存** | > 70% | > 80% |
| **Swap** | > 20% | > 50% |
| **硬碟** | > 70% | > 80% |
| **Chrome 進程** | > 40 | > 50 |

**Cron Job**:
```json
{
  "id": "ee6772fe-6760-4188-a07c-1c9f63308e6e",
  "name": "System Resource Monitor",
  "schedule": "0 * * * * (每小時)"
}
```

---

### 2️⃣ system_analyzer.sh - 詳細分析腳本

**路徑**: `/home/admin/.openclaw/workspace/scripts/system_analyzer.sh`

**功能**:
- 詳細的系統資源分析
- Top 10 內存/CPU 用戶
- 硬碟使用詳情
- 綜合評估與優化建議

**執行方式**:
```bash
/home/admin/.openclaw/workspace/scripts/system_analyzer.sh
```

---

## 📊 當前系統狀態

### 即時狀態 (2026-02-28 11:47 AM)

```
💾 內存：37.5% (2.7Gi / 7.1Gi)     ✅ 正常
🔄 Swap: 0.0% (0B / 4.0Gi)         ✅ 正常
💿 硬碟：67% (32G / 49G)           🟡 注意
🌐 Chrome: 30 個進程               🟡 注意
⚡ CPU: ~1.2%                      ✅ 正常
```

**整體評估**: ✅ 良好

---

## 📁 目錄結構

```
/home/admin/.openclaw/workspace/
├── scripts/
│   ├── system_monitor.sh      # 自動監控腳本
│   ├── system_analyzer.sh     # 詳細分析腳本
│   ├── monitor_memory.sh      # 舊內存監控 (已整合)
│   └── memory_optimizer.sh    # 內存優化 (已整合)
├── logs/
│   ├── system_monitor.log     # 系統監控日誌
│   ├── system_alerts.log      # 系統警報日誌
│   └── memory_alerts.log      # 舊內存警報 (已整合)
└── docs/
    └── system_monitoring.md   # 本文檔
```

---

## 🔔 警報通知

### Discord 通知格式

```
📊 系統資源監控報告
⏰ 時間：2026-02-28 11:47:11

資源使用狀況:
├─ 💾 內存：38% (2796324KB / 7445144KB)
├─ 🔄 Swap: 0% (0KB / 4194300KB)
├─ 💿 硬碟：67% (32G / 49G)
├─ 🌐 Chrome: 30 個進程
└─ ⚡ CPU: 1.2%

狀態：🟢 正常 - 系統運行良好
```

### 警報級別

| 級別 | 條件 | 動作 |
|------|------|------|
| 🟢 **正常** | 所有指標 < 70% | 記錄日誌 |
| 🟡 **警告** | 任一指標 70-80% | 記錄 + Discord 通知 |
| 🔴 **嚴重** | 任一指標 > 80% | 記錄 + Discord 通知 + 優化建議 |

---

## 🛠️ 使用指南

### 查看當前狀態

```bash
# 快速檢查
/home/admin/.openclaw/workspace/scripts/system_analyzer.sh

# 查看監控日誌
tail -20 /home/admin/.openclaw/workspace/logs/system_monitor.log

# 查看警報歷史
tail -20 /home/admin/.openclaw/workspace/logs/system_alerts.log
```

### 手動觸發監控

```bash
# 執行監控腳本
/home/admin/.openclaw/workspace/scripts/system_monitor.sh

# 執行 Cron Job
cron run ee6772fe-6760-4188-a07c-1c9f63308e6e
```

### 配置閾值

編輯 `system_monitor.sh`:
```bash
MEMORY_THRESHOLD=80      # 內存警告閾值
DISK_THRESHOLD=80        # 硬碟警告閾值
SWAP_THRESHOLD=50        # Swap 警告閾值
CHROME_PROCESS_THRESHOLD=50  # Chrome 進程警告閾值
```

---

## 📈 歷史趨勢

### 內存使用趨勢

| 時間 | 使用率 | 狀態 |
|------|--------|------|
| 優化前 (11:30) | 79% | 🔴 嚴重 |
| 優化後 (11:38) | 37% | ✅ 正常 |
| 當前 (11:47) | 38% | ✅ 正常 |

### 硬碟使用趨勢

| 時間 | 使用率 | 狀態 |
|------|--------|------|
| 當前 | 67% | 🟡 注意 |

**建議**: 當硬碟使用超過 70% 時開始清理

---

## 🎯 優化建議

### 立即執行 (已完成 ✅)
- [x] 配置 Swap 空間 (4 GB)
- [x] 重啟 Browser 釋放內存
- [x] 設置自動監控

### 定期維護
- [ ] **每週**: 重啟 Browser (建議：週日 02:00)
- [ ] **每月**: 清理硬碟 (>70% 時)
- [ ] **每月**: 審查 Chrome 擴展

### 硬碟清理建議

```bash
# 查看最大的 20 個文件
du -ah /home/admin | sort -rh | head -20

# 清理 Browser Cache
rm -rf /home/admin/.openclaw/browser/openclaw/user-data/Default/Cache/*

# 清理舊日誌
find /home/admin/.openclaw/workspace/logs -name "*.log" -mtime +30 -delete

# 查看可歸檔文件
ls -lh /home/admin/.openclaw/memory/
```

---

## 📋 相關 Cron Jobs

### ✅ 啟用中

| ID | 名稱 | 頻率 | 說明 |
|----|------|------|------|
| `ee6772fe-6760-4188-a07c-1c9f63308e6e` | System Resource Monitor | 每小時 | 整合監控（內存 + 硬碟 + CPU + Chrome） |

### ❌ 已停用

| ID | 名稱 | 停用時間 | 原因 |
|----|------|---------|------|
| `164faa52-d172-4601-a66e-18570d2f9d89` | Memory Monitor | 2026-02-28 | 已整合到 System Resource Monitor |
| `7f9c1d38-078f-4a4b-8630-eb9277a30fd7` | Disk Space Monitor | 2026-02-28 | 已整合到 System Resource Monitor |

---

## 🔧 故障排除

### 問題：未收到 Discord 警報

**檢查**:
1. Webhook URL 是否正確
2. Discord 頻道權限
3. 日誌文件：`tail /home/admin/.openclaw/workspace/logs/system_alerts.log`

### 問題：監控腳本執行失敗

**檢查**:
1. 腳本權限：`chmod +x /home/admin/.openclaw/workspace/scripts/system_monitor.sh`
2. Cron Job 狀態：`cron list`
3. 系統日誌：`journalctl -u cron`

### 問題：誤報警報

**解決**:
1. 調整閾值（編輯腳本）
2. 檢查是否為短暫峰值
3. 查看歷史趨勢確認

---

## 📝 最佳實踐

### ✅ 建議做法
1. **定期檢視**: 每週查看監控報告
2. **趨勢分析**: 關注長期趨勢而非單點數據
3. **預防性維護**: 在達到閾值前主動優化
4. **日誌保留**: 保留至少 30 天的監控日誌

### ❌ 避免做法
1. 忽略持續增长的趨勢
2. 設置過低的閾值（導致警報疲勞）
3. 設置過高的閾值（失去預警意義）
4. 只監控不行動

---

## 📞 支持

**創建時間**: 2026-02-28  
**版本**: 1.0  
**維護**: AI Assistant  
**下次檢視**: 2026-03-07

**相關文檔**:
- `/home/admin/.openclaw/workspace/docs/memory_optimization_report_2026-02-28.md`
- `/home/admin/.openclaw/workspace/scripts/system_monitor.sh`
- `/home/admin/.openclaw/workspace/scripts/system_analyzer.sh`

---

*最後更新：2026-02-28 11:47 AM*  
*系統狀態：✅ 正常運行*
