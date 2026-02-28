#!/bin/bash
# 內存監控腳本 - 當內存使用超過 80% 時發送警報

THRESHOLD=80
DISCORD_WEBHOOK="https://discord.com/api/webhooks/1470240479525212181/feekMInHeAIS-hMPuzthOTTIdeNcOuosYSJkqPT4etQgeRAXHs6QCIt7dm1BEuI6YkYi"

# 獲取內存使用率
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')

# 獲取 Chrome 進程數量
CHROME_COUNT=$(ps aux | grep -c "[c]hrome")

# 獲取前 5 個內存用戶
TOP_MEMORY=$(ps aux --sort=-%mem | head -6 | tail -5 | awk '{print $11, $4"%"}')

# 獲取當前時間
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# 創建警報訊息
MESSAGE="🚨 **內存警報**\n\n"
MESSAGE+="📊 **使用率**: ${MEMORY_USAGE}%\n"
MESSAGE+="🌐 **Chrome 進程**: ${CHROME_COUNT} 個\n"
MESSAGE+="⏰ **時間**: ${TIMESTAMP}\n\n"
MESSAGE+="**Top 5 內存用戶**:\n\`\`\`\n${TOP_MEMORY}\n\`\`\`\n\n"

if [ "$MEMORY_USAGE" -gt "$THRESHOLD" ]; then
    MESSAGE+="⚠️ 內存使用率超過 ${THRESHOLD}%！建議執行優化。\n\n"
    MESSAGE+="**建議操作**:\n"
    MESSAGE+="1. 重啟 Browser: \`openclaw browser restart\`\n"
    MESSAGE+="2. 關閉閒置 Chrome 分頁\n"
    MESSAGE+="3. 檢查是否有內存洩漏"
    
    # 發送 Discord 通知
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"content\": \"${MESSAGE}\"}" \
        "$DISCORD_WEBHOOK" > /dev/null
    
    # 記錄到日誌
    echo "[$TIMESTAMP] 內存警報：${MEMORY_USAGE}%, Chrome 進程：${CHROME_COUNT}" >> /home/admin/.openclaw/workspace/logs/memory_alerts.log
fi

# 輸出狀態（用於 cron 執行）
echo "[$TIMESTAMP] 內存使用率：${MEMORY_USAGE}%, Chrome: ${CHROME_COUNT}, Swap: $(free | grep Swap | awk '{printf("%.0f", $3/$2 * 100.0)}')%"
