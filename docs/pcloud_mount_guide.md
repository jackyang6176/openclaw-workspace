# pCloudDrive 掛載/卸載指南 - 2026-02-28

## 📊 系統狀態

**檢查時間**: 2026-02-28 20:44

### 當前狀態

| 項目 | 狀態 |
|------|------|
| **fusermount** | ✅ 已安裝 (`/usr/bin/fusermount`) |
| **fusermount3** | ✅ 已安裝 (`/usr/bin/fusermount3`) |
| **pcloudcc** | ❌ 未運行 |
| **pCloudDrive** | ⚠️ 目錄存在但未掛載 |
| **FUSE** | ✅ 已安裝 (fuse3 3.14.0) |

---

## 🔧 fusermount 命令位置

**已安裝**:
```bash
/usr/bin/fusermount    # FUSE 2.x
/usr/bin/fusermount3   # FUSE 3.x (推薦使用)
```

**注意**: pCloud 使用 FUSE 3.x，建議使用 `fusermount3`

---

## 📋 pCloudDrive 掛載/卸載命令

### 方法 1: 使用 pcloudcc (推薦)

#### 啟動 pCloudDrive

```bash
# 啟動 pcloudcc (會自動掛載 pCloudDrive)
pcloudcc
```

#### 停止 pCloudDrive

```bash
# 方法 1: 使用 pcloudcc 自帶的停止功能
pcloudcc --stop

# 方法 2: 終止進程
pkill pcloudcc

# 方法 3: 使用 fusermount3 卸載
fusermount3 -u /home/admin/pCloudDrive
```

---

### 方法 2: 使用 fusermount3

#### 卸載 pCloudDrive

```bash
# 卸載 pCloudDrive
fusermount3 -u /home/admin/pCloudDrive

# 或強制卸載 (如果普通卸載失敗)
fusermount3 -uz /home/admin/pCloudDrive
```

#### 檢查掛載狀態

```bash
# 檢查是否已掛載
mount | grep pcloud

# 或
df -h | grep pcloud
```

---

### 方法 3: 使用 umount

```bash
# 標準卸載命令
umount /home/admin/pCloudDrive

# 強制卸載
umount -f /home/admin/pCloudDrive

# 懶卸載 (等待所有訪問完成)
umount -l /home/admin/pCloudDrive
```

---

## 🚀 完整操作示例

### 啟動 pCloudDrive

```bash
# 1. 啟動 pcloudcc
pcloudcc

# 2. 等待幾秒讓掛載完成
sleep 5

# 3. 驗證掛載
mount | grep pcloud
ls -la /home/admin/pCloudDrive/
```

### 卸載 pCloudDrive

```bash
# 1. 停止 pcloudcc 進程
pkill pcloudcc

# 2. 等待進程完全停止
sleep 2

# 3. 卸載 pCloudDrive
fusermount3 -u /home/admin/pCloudDrive

# 4. 驗證卸載
mount | grep pcloud  # 應該無輸出
```

---

## ⚠️ 常見問題

### 問題 1: "Device or resource busy"

**錯誤**:
```
fusermount3: Device or resource busy
```

**原因**: 有進程正在使用 pCloudDrive

**解決方案**:
```bash
# 1. 找出使用 pCloudDrive 的進程
lsof +D /home/admin/pCloudDrive

# 2. 終止這些進程
fuser -km /home/admin/pCloudDrive

# 3. 強制卸載
fusermount3 -uz /home/admin/pCloudDrive
```

### 問題 2: "Permission denied"

**錯誤**:
```
fusermount3: Permission denied
```

**解決方案**:
```bash
# 確保使用正確的用戶 (不要用 sudo)
fusermount3 -u /home/admin/pCloudDrive

# 如果是 root 掛載的，需要用 root 卸載
sudo fusermount3 -u /home/admin/pCloudDrive
```

### 問題 3: "Not mounted"

**錯誤**:
```
fusermount3: Not mounted
```

**原因**: pCloudDrive 未掛載

**解決方案**:
```bash
# 檢查掛載狀態
mount | grep pcloud

# 如果未掛載，啟動 pcloudcc
pcloudcc
```

### 問題 4: pcloudcc 命令不存在

**錯誤**:
```
bash: pcloudcc: command not found
```

**解決方案**:
```bash
# 檢查 pcloudcc 路徑
which pcloudcc

# 如果未找到，需要安裝 pCloud
# 下載：https://www.pcloud.com/download/
# 或檢查是否在 /usr/local/bin/
ls -la /usr/local/bin/pcloudcc
```

---

## 📊 當前系統配置

### FUSE 版本

```bash
$ fusermount3 --version
fusermount3 version: 3.14.0
```

### pcloudcc 路徑

```bash
$ which pcloudcc
/usr/local/bin/pcloudcc
```

### pCloudDrive 目錄

```bash
$ ls -la /home/admin/pCloudDrive/
total 12
drwxr-xr-x  3 admin admin 4096 Feb 23 10:46 .
drwxr-x--- 35 admin admin 4096 Feb 28 20:25 ..
drwxrwxr-x  9 admin admin 4096 Feb 28 13:39 openclaw
```

---

## 🔍 診斷命令

### 檢查 pCloudDrive 狀態

```bash
# 1. 檢查 pcloudcc 進程
ps aux | grep pcloudcc

# 2. 檢查掛載狀態
mount | grep pcloud

# 3. 檢查 FUSE 模塊
lsmod | grep fuse

# 4. 檢查 pCloudDrive 目錄
ls -la /home/admin/pCloudDrive/
```

### 測試掛載/卸載

```bash
# 1. 啟動 pcloudcc
pcloudcc &

# 2. 等待掛載
sleep 5

# 3. 驗證
ls /home/admin/pCloudDrive/

# 4. 停止
pkill pcloudcc
fusermount3 -u /home/admin/pCloudDrive

# 5. 驗證卸載
ls /home/admin/pCloudDrive/  # 應該只能看到空目錄
```

---

## 💡 最佳實踐

### 1. 使用腳本管理

創建啟動腳本 `~/scripts/start_pcloud.sh`:
```bash
#!/bin/bash
echo "啟動 pCloudDrive..."
pcloudcc &
sleep 5
if mount | grep -q pcloud; then
    echo "✅ pCloudDrive 掛載成功"
else
    echo "❌ pCloudDrive 掛載失敗"
    exit 1
fi
```

創建停止腳本 `~/scripts/stop_pcloud.sh`:
```bash
#!/bin/bash
echo "停止 pCloudDrive..."
pkill pcloudcc
sleep 2
fusermount3 -u /home/admin/pCloudDrive 2>/dev/null
if mount | grep -q pcloud; then
    echo "⚠️  pCloudDrive 仍在掛載，嘗試強制卸載..."
    fusermount3 -uz /home/admin/pCloudDrive
fi
echo "✅ pCloudDrive 已停止"
```

### 2. 開機自動啟動

```bash
# 添加到 ~/.bashrc 或 ~/.profile
pcloudcc &
```

### 3. 定期檢查狀態

```bash
# 添加到 crontab
# 每小時檢查 pcloudcc 是否運行
0 * * * * pgrep pcloudcc >/dev/null || pcloudcc &
```

---

## 📞 相關文件

- **掛載指南**: 本文檔
- **pCloudDrive 目錄**: `/home/admin/pCloudDrive/`
- **pcloudcc 二進制**: `/usr/local/bin/pcloudcc`
- **fusermount3**: `/usr/bin/fusermount3`

---

*創建時間：2026-02-28 20:44*  
*創建者：AI Assistant*  
*系統：Ubuntu 24.04, FUSE 3.14.0*
