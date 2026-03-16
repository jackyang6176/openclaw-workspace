# 磁碟空間清理報告 - 2026-03-01

## 📊 當前狀態

**磁碟使用**: 40G / 49G (85%)  
**可用空間**: 7.1 GB  
**狀態**: ⚠️ 需要注意

---

## 🗑️ 可清理項目

### 1️⃣ 臨時文件 (/tmp) - **可釋放 ~3.6 GB**

| 目錄 | 大小 | 說明 |
|------|------|------|
| `/tmp/pip-unpack-*` | ~3.3 GB | pip 安裝臨時文件 |
| `/tmp/tmp*` | ~255 MB | 系統臨時文件 |
| `/tmp/node-compile-cache` | 37 MB | Node.js 編譯緩存 |
| `/tmp/psync_err.log` | 31 MB | 同步錯誤日誌 |
| `/tmp/jiti` | 25 MB | Jiti 緩存 |
| `/tmp/openclaw-*` | ~20 MB | OpenClaw 臨時文件 |
| `/tmp/Kronos` | 19 MB | Kronos 測試文件 |
| `/tmp/fubon_neo*` | ~9 MB | Fubon SDK 安裝包 |

**建議**: ✅ **清理** (這些是臨時文件，可以安全刪除)

---

### 2️⃣ OpenClaw 備份文件 - **可釋放 ~30 KB**

```
openclaw.json.bak      (5.9 KB)
openclaw.json.bak.1    (6.1 KB)
openclaw.json.bak.2    (6.1 KB)
openclaw.json.bak.3    (6.1 KB)
openclaw.json.bak.4    (5.7 KB)
```

**建議**: ⚠️ **保留最近 3 個**，刪除舊的

---

### 3️⃣ 舊的虛擬環境 - **可釋放 ~4 KB**

- `/home/admin/china_stock_env` (4 KB，空目錄)

**建議**: ✅ **刪除**

---

### 4️⃣ 瀏覽器緩存 - **可釋放 ~17 MB**

- `/home/admin/.openclaw/browser/openclaw/user-data/Default/Cache/`

**建議**: ⚠️ **可選清理** (可能影響瀏覽器性能)

---

### 5️⃣ 已歸檔的 Gmail Monitor - **已在 pCloudDrive**

- `/home/admin/pCloudDrive/openclaw/archived_projects/gmail_monitor/` (433 MB)

**建議**: ✅ **已歸檔，無需清理**

---

## 📋 清理計劃

### 立即執行 (安全)

```bash
# 1. 清理 pip 臨時文件
rm -rf /tmp/pip-*

# 2. 清理舊的臨時文件
rm -rf /tmp/tmp*

# 3. 清理 Node.js 緩存
rm -rf /tmp/node-compile-cache

# 4. 清理舊日誌
rm -f /tmp/psync_err.log

# 5. 清理舊虛擬環境
rm -rf /home/admin/china_stock_env

# 6. 清理舊的 OpenClaw 備份 (保留最近 3 個)
rm /home/admin/.openclaw/openclaw.json.bak.3
rm /home/admin/.openclaw/openclaw.json.bak.4
```

**預計釋放**: ~3.6 GB

### 可選清理

```bash
# 清理瀏覽器緩存 (可選)
rm -rf /home/admin/.openclaw/browser/openclaw/user-data/Default/Cache/*

# 清理 Kronos 測試文件
rm -rf /tmp/Kronos

# 清理 Fubon 安裝包
rm -f /tmp/fubon_neo*
```

**預計額外釋放**: ~50 MB

---

## 📊 清理後預期

| 項目 | 清理前 | 清理後 | 釋放 |
|------|--------|--------|------|
| **磁碟使用** | 40 GB | 36.4 GB | -3.6 GB |
| **可用空間** | 7.1 GB | 10.7 GB | +3.6 GB |
| **使用率** | 85% | 74% | -11% |

---

## ✅ 清理命令

### 完整清理腳本

```bash
#!/bin/bash
# /home/admin/.openclaw/workspace/scripts/cleanup_disk.sh

echo "=== 開始磁碟清理 ==="

# 1. 清理 pip 臨時文件
echo "清理 pip 臨時文件..."
rm -rf /tmp/pip-*

# 2. 清理舊的臨時文件
echo "清理舊的臨時文件..."
rm -rf /tmp/tmp*

# 3. 清理 Node.js 緩存
echo "清理 Node.js 緩存..."
rm -rf /tmp/node-compile-cache

# 4. 清理舊日誌
echo "清理舊日誌..."
rm -f /tmp/psync_err.log

# 5. 清理舊虛擬環境
echo "清理舊虛擬環境..."
rm -rf /home/admin/china_stock_env

# 6. 清理舊的 OpenClaw 備份
echo "清理舊的 OpenClaw 備份..."
rm -f /home/admin/.openclaw/openclaw.json.bak.3
rm -f /home/admin/.openclaw/openclaw.json.bak.4

# 7. 可選：清理瀏覽器緩存
# echo "清理瀏覽器緩存..."
# rm -rf /home/admin/.openclaw/browser/*/user-data/Default/Cache/*

# 8. 可選：清理 Kronos 測試文件
# rm -rf /tmp/Kronos

# 9. 可選：清理 Fubon 安裝包
# rm -f /tmp/fubon_neo*

echo "=== 清理完成 ==="
echo ""
echo "磁碟空間:"
df -h /
```

---

## 🎯 建議

### 立即執行
- ✅ 清理 /tmp/pip-* (~3.3 GB)
- ✅ 清理 /tmp/tmp* (~255 MB)
- ✅ 清理舊虛擬環境
- ✅ 清理舊備份文件

### 定期執行
- 📅 每週清理 /tmp 目錄
- 📅 每月檢查虛擬環境
- 📅 保留最近 3 個配置文件備份

### 長期維護
- 📊 監控磁碟使用率
- 📊 設置 80% 警告閾值
- 📊 自動清理臨時文件

---

*報告生成時間：2026-03-01 16:45*  
*生成者：AI Assistant*  
*建議清理：~3.6 GB*
