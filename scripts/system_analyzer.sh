#!/bin/bash
# 系統資源詳細分析腳本

echo "======================================"
echo "🖥️  系統資源詳細分析"
echo "======================================"
echo "時間：$(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ============================================
# 1. 內存分析
# ============================================
echo "=== 💾 內存使用分析 ==="
free -h
echo ""

# 內存使用率
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
echo "內存使用率：${MEMORY_USAGE}%"

# 評估
if (( $(echo "$MEMORY_USAGE < 50" | bc -l) )); then
    echo "狀態：✅ 正常"
elif (( $(echo "$MEMORY_USAGE < 70" | bc -l) )); then
    echo "狀態：🟡 注意"
elif (( $(echo "$MEMORY_USAGE < 85" | bc -l) )); then
    echo "狀態：🟠 警告"
else
    echo "狀態：🔴 嚴重"
fi
echo ""

# ============================================
# 2. Swap 分析
# ============================================
echo "=== 🔄 Swap 分析 ==="
if [ -f /proc/swaps ]; then
    cat /proc/swaps 2>/dev/null || echo "無 Swap"
else
    echo "無 Swap"
fi
echo ""

SWAP_USAGE=$(free | grep Swap | awk '{if($2>0) printf("%.1f", $3/$2 * 100.0); else print "0"}')
echo "Swap 使用率：${SWAP_USAGE}%"
echo ""

# ============================================
# 3. 硬碟分析
# ============================================
echo "=== 💿 硬碟使用分析 ==="
df -h /
echo ""

echo "=== 主要目錄大小 ==="
du -sh /home/admin/.openclaw/* 2>/dev/null | sort -hr | head -10
echo ""

echo "=== 硬碟使用率評估 ==="
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
echo "根目錄使用率：${DISK_USAGE}%"

if [ "$DISK_USAGE" -lt 50 ]; then
    echo "狀態：✅ 正常"
elif [ "$DISK_USAGE" -lt 70 ]; then
    echo "狀態：🟡 注意"
elif [ "$DISK_USAGE" -lt 85 ]; then
    echo "狀態：🟠 警告"
else
    echo "狀態：🔴 嚴重"
fi
echo ""

# ============================================
# 4. Chrome 分析
# ============================================
echo "=== 🌐 Chrome 瀏覽器分析 ==="
CHROME_COUNT=$(ps aux | grep -c "[c]hrome")
echo "Chrome 進程數：${CHROME_COUNT} 個"

CHROME_MEM=$(ps aux --sort=-%mem | grep "[c]hrome" | awk '{sum+=$6} END {printf("%.0f", sum/1024)}')
echo "Chrome 總內存：${CHROME_MEM} MB"

if [ "$CHROME_COUNT" -lt 30 ]; then
    echo "狀態：✅ 正常"
elif [ "$CHROME_COUNT" -lt 50 ]; then
    echo "狀態：🟡 注意"
else
    echo "狀態：🔴 警告 - 建議重啟 Browser"
fi
echo ""

# ============================================
# 5. CPU 分析
# ============================================
echo "=== ⚡ CPU 分析 ==="
echo "CPU 使用率："
top -bn1 | grep "Cpu(s)" | head -1
echo ""

echo "=== Top 5 CPU 用戶 ==="
ps aux --sort=-%cpu | head -6 | tail -5 | awk '{printf "%-20s %6s %8s\n", $11, $3"%", $4"%"}'
echo ""

# ============================================
# 6. Top 10 內存用戶
# ============================================
echo "=== 📊 Top 10 內存用戶 ==="
ps aux --sort=-%mem | head -11 | tail -10 | awk '{printf "%-20s %6s %8s\n", $11, $4"%", $6/1024" MB"}'
echo ""

# ============================================
# 7. 系統負載
# ============================================
echo "=== 📈 系統負載 ==="
uptime
echo ""

# ============================================
# 8. 綜合評估與建議
# ============================================
echo "=== 💡 綜合評估與建議 ==="

OVERALL_STATUS="✅ 良好"
RECOMMENDATIONS=""

# 檢查各项指標
if (( $(echo "$MEMORY_USAGE >= 85" | bc -l) )); then
    OVERALL_STATUS="🔴 需要立即優化"
    RECOMMENDATIONS+="• 緊急：內存使用過高，立即重啟 Browser\n"
fi

if [ "$DISK_USAGE" -ge 85 ]; then
    OVERALL_STATUS="🔴 需要立即優化"
    RECOMMENDATIONS+="• 緊急：硬碟空間不足，清理大文件\n"
fi

if [ "$CHROME_COUNT" -ge 50 ]; then
    if [ "$OVERALL_STATUS" != "🔴 需要立即優化" ]; then
        OVERALL_STATUS="🟠 需要優化"
    fi
    RECOMMENDATIONS+="• 建議：Chrome 進程過多，重啟 Browser\n"
fi

if (( $(echo "$MEMORY_USAGE >= 70" | bc -l) )) && [ "$OVERALL_STATUS" = "✅ 良好" ]; then
    OVERALL_STATUS="🟡 需要注意"
    RECOMMENDATIONS+="• 注意：內存使用中等，建議監控\n"
fi

if [ "$DISK_USAGE" -ge 70 ] && [ "$OVERALL_STATUS" = "✅ 良好" ]; then
    OVERALL_STATUS="🟡 需要注意"
    RECOMMENDATIONS+="• 注意：硬碟使用中等，建議清理\n"
fi

echo "系統整體狀態：${OVERALL_STATUS}"
echo ""

if [ -n "$RECOMMENDATIONS" ]; then
    echo "優化建議:"
    echo -e "$RECOMMENDATIONS"
fi

# 快速優化命令參考
echo "=== 🛠️ 快速優化命令 ==="
echo "# 重啟 Browser"
echo "openclaw browser restart"
echo ""
echo "# 查看大文件"
echo "du -ah /home/admin | sort -rh | head -20"
echo ""
echo "# 清理 Chrome Cache"
echo "rm -rf /home/admin/.openclaw/browser/openclaw/user-data/Default/Cache/*"
echo ""
echo "# 查看系統資源趨勢"
echo "tail -f /home/admin/.openclaw/workspace/logs/system_monitor.log"
echo ""

echo "======================================"
