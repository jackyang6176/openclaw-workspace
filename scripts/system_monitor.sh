#!/bin/bash
# 系統資源監控腳本 - 整合內存、硬碟、CPU 監控
# 當資源使用超過閾值時發送 Discord 警報

# 配置
DISCORD_WEBHOOK="https://discord.com/api/webhooks/1470240479525212181/feekMInHeAIS-hMPuzthOTTIdeNcOuosYSJkqPT4etQgeRAXHs6QCIt7dm1BEuI6YkYi"
LOG_DIR="/home/admin/.openclaw/workspace/logs"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# 閾值配置
MEMORY_THRESHOLD=80
DISK_THRESHOLD=80
SWAP_THRESHOLD=50
CHROME_PROCESS_THRESHOLD=50

# 創建日誌目錄
mkdir -p "$LOG_DIR"

# ============================================
# 1. 內存監控
# ============================================
MEMORY_TOTAL=$(free | grep Mem | awk '{print $2}')
MEMORY_USED=$(free | grep Mem | awk '{print $3}')
MEMORY_AVAILABLE=$(free | grep Mem | awk '{print $7}')
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')
SWAP_TOTAL=$(free | grep Swap | awk '{print $2}')
SWAP_USED=$(free | grep Swap | awk '{print $3}')
SWAP_USAGE=0
if [ "$SWAP_TOTAL" -gt 0 ]; then
    SWAP_USAGE=$(free | grep Swap | awk '{printf("%.0f", $3/$2 * 100.0)}')
fi

# Chrome 進程監控
CHROME_COUNT=$(ps aux | grep -c "[c]hrome")

# ============================================
# 2. 硬碟監控
# ============================================
DISK_USAGE=$(df -h /home | awk 'NR==2 {print $5}' | sed 's/%//')
DISK_TOTAL=$(df -h /home | awk 'NR==2 {print $2}')
DISK_USED=$(df -h /home | awk 'NR==2 {print $3}')
DISK_AVAILABLE=$(df -h /home | awk 'NR==2 {print $4}')

# ============================================
# 3. CPU 監控
# ============================================
CPU_IDLE=$(top -bn1 | grep "Cpu(s)" | awk '{print $8}' | cut -d'%' -f1)
if [ -z "$CPU_IDLE" ]; then
    CPU_IDLE=$(top -bn1 | grep "%Cpu" | awk '{print $8}' | cut -d'%' -f1)
fi
if [ -z "$CPU_IDLE" ]; then
    CPU_IDLE=95.0
fi
CPU_USAGE=$(echo "100 - $CPU_IDLE" | bc 2>/dev/null || echo "5.0")

# ============================================
# 4. 生成警報訊息
# ============================================
ALERT_LEVEL="normal"
ALERT_MESSAGES=""

# 檢查內存
if [ "$MEMORY_USAGE" -gt "$MEMORY_THRESHOLD" ]; then
    ALERT_LEVEL="critical"
    ALERT_MESSAGES+="🔴 **內存過高**: ${MEMORY_USAGE}% (閾值：${MEMORY_THRESHOLD}%)\n"
elif [ "$MEMORY_USAGE" -gt 70 ]; then
    if [ "$ALERT_LEVEL" != "critical" ]; then ALERT_LEVEL="warning"; fi
    ALERT_MESSAGES+="🟡 **內存警告**: ${MEMORY_USAGE}% (閾值：${MEMORY_THRESHOLD}%)\n"
fi

# 檢查 Swap
if [ "$SWAP_USAGE" -gt "$SWAP_THRESHOLD" ]; then
    if [ "$ALERT_LEVEL" != "critical" ]; then ALERT_LEVEL="critical"; fi
    ALERT_MESSAGES+="🔴 **Swap 過高**: ${SWAP_USAGE}% (閾值：${SWAP_THRESHOLD}%)\n"
fi

# 檢查 Chrome 進程
if [ "$CHROME_COUNT" -gt "$CHROME_PROCESS_THRESHOLD" ]; then
    if [ "$ALERT_LEVEL" != "critical" ]; then ALERT_LEVEL="warning"; fi
    ALERT_MESSAGES+="🟡 **Chrome 進程過多**: ${CHROME_COUNT} 個 (閾值：${CHROME_PROCESS_THRESHOLD})\n"
fi

# 檢查硬碟
if [ "$DISK_USAGE" -gt "$DISK_THRESHOLD" ]; then
    ALERT_LEVEL="critical"
    ALERT_MESSAGES+="🔴 **硬碟過滿**: ${DISK_USAGE}% (閾值：${DISK_THRESHOLD}%)\n"
elif [ "$DISK_USAGE" -gt 70 ]; then
    if [ "$ALERT_LEVEL" != "critical" ]; then ALERT_LEVEL="warning"; fi
    ALERT_MESSAGES+="🟡 **硬碟警告**: ${DISK_USAGE}% (閾值：${DISK_THRESHOLD}%)\n"
fi

# ============================================
# 5. 創建狀態報告
# ============================================
STATUS_REPORT="📊 **系統資源監控報告**\n"
STATUS_REPORT+="⏰ **時間**: ${TIMESTAMP}\n\n"

STATUS_REPORT+="**資源使用狀況**:\n"
STATUS_REPORT+="├─ 💾 **內存**: ${MEMORY_USAGE}% (${MEMORY_USED}KB / ${MEMORY_TOTAL}KB)\n"
STATUS_REPORT+="├─ 🔄 **Swap**: ${SWAP_USAGE}% (${SWAP_USED}KB / ${SWAP_TOTAL}KB)\n"
STATUS_REPORT+="├─ 💿 **硬碟**: ${DISK_USAGE}% (${DISK_USED} / ${DISK_TOTAL})\n"
STATUS_REPORT+="├─ 🌐 **Chrome**: ${CHROME_COUNT} 個進程\n"
STATUS_REPORT+="└─ ⚡ **CPU**: ${CPU_USAGE}%\n\n"

if [ -n "$ALERT_MESSAGES" ]; then
    STATUS_REPORT+="**警報**:\n${ALERT_MESSAGES}\n"
fi

# 添加優化建議
if [ "$ALERT_LEVEL" = "critical" ]; then
    STATUS_REPORT+="🔧 **建議操作**:\n"
    if [ "$MEMORY_USAGE" -gt "$MEMORY_THRESHOLD" ]; then
        STATUS_REPORT+="• 重啟 Browser: \`openclaw browser restart\`\n"
    fi
    if [ "$DISK_USAGE" -gt "$DISK_THRESHOLD" ]; then
        STATUS_REPORT+="• 清理大文件：\`du -sh /home/admin/* | sort -hr | head -10\`\n"
    fi
    if [ "$CHROME_COUNT" -gt "$CHROME_PROCESS_THRESHOLD" ]; then
        STATUS_REPORT+="• 關閉閒置 Chrome 分頁\n"
    fi
fi

STATUS_REPORT+="\n**狀態**: "
case $ALERT_LEVEL in
    "critical")
        STATUS_REPORT+="🔴 嚴重 - 需要立即處理"
        ;;
    "warning")
        STATUS_REPORT+="🟡 警告 - 建議關注"
        ;;
    *)
        STATUS_REPORT+="🟢 正常 - 系統運行良好"
        ;;
esac

# ============================================
# 6. 發送警報（如果需要）
# ============================================
if [ "$ALERT_LEVEL" != "normal" ]; then
    # 發送 Discord 通知
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"content\": \"${STATUS_REPORT}\"}" \
        "$DISCORD_WEBHOOK" > /dev/null
    
    # 記錄到日誌
    echo "[${TIMESTAMP}] ${ALERT_LEVEL^^}: 內存=${MEMORY_USAGE}%, Swap=${SWAP_USAGE}%, 硬碟=${DISK_USAGE}%, Chrome=${CHROME_COUNT}" >> "${LOG_DIR}/system_alerts.log"
fi

# 記錄常規檢查
echo "[${TIMESTAMP}] ${ALERT_LEVEL}: 內存=${MEMORY_USAGE}%, 硬碟=${DISK_USAGE}%, Chrome=${CHROME_COUNT}" >> "${LOG_DIR}/system_monitor.log"

# 輸出狀態
echo "$STATUS_REPORT"

# ============================================
# 7. 返回狀態碼
# ============================================
case $ALERT_LEVEL in
    "critical")
        exit 2
        ;;
    "warning")
        exit 1
        ;;
    *)
        exit 0
        ;;
esac
