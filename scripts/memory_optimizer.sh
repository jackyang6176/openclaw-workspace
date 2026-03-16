#!/bin/bash
# 內存優化建議腳本 - 分析並提供優化建議

echo "======================================"
echo "📊 內存使用分析報告"
echo "======================================"
echo ""

# 基本統計
echo "=== 內存總覽 ==="
free -h
echo ""

# Swap 狀態
echo "=== Swap 狀態 ==="
cat /proc/swaps 2>/dev/null || echo "無 Swap"
echo ""

# Chrome 分析
echo "=== Chrome 分析 ==="
CHROME_COUNT=$(ps aux | grep -c "[c]hrome")
CHROME_MEM=$(ps aux --sort=-%mem | grep "[c]hrome" | awk '{sum+=$6} END {print sum/1024}')
echo "Chrome 進程數：$CHROME_COUNT 個"
echo "Chrome 總內存：${CHROME_MEM} MB"
echo ""

# Top 10 進程
echo "=== Top 10 內存用戶 ==="
ps aux --sort=-%mem | head -11 | tail -10 | awk '{printf "%-20s %8s %8s\n", $11, $4"%", $6/1024" MB"}'
echo ""

# 優化建議
echo "=== 優化建議 ==="

MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')

if [ "$MEMORY_USAGE" -lt 50 ]; then
    echo "✅ 內存使用正常 (${MEMORY_USAGE}%) - 無需優化"
elif [ "$MEMORY_USAGE" -lt 70 ]; then
    echo "⚠️  內存使用中等 (${MEMORY_USAGE}%) - 可選優化"
    echo "   建議：關閉不用的 Chrome 分頁"
elif [ "$MEMORY_USAGE" -lt 85 ]; then
    echo "🟡 內存使用較高 (${MEMORY_USAGE}%) - 建議優化"
    echo "   建議操作："
    echo "   1. 重啟 Browser: openclaw browser restart"
    echo "   2. 關閉閒置 Chrome 分頁"
    echo "   3. 檢查是否有內存洩漏"
else
    echo "🔴 內存使用過高 (${MEMORY_USAGE}%) - 立即優化！"
    echo "   緊急操作："
    echo "   1. 立即重啟 Browser"
    echo "   2. 終結舊的 Chrome 進程"
    echo "   3. 考慮增加系統內存"
fi

echo ""
echo "=== Browser 狀態 ==="
if pgrep -f "chrome.*18800" > /dev/null; then
    echo "Browser: ✅ 運行中"
else
    echo "Browser: ❌ 未運行"
fi

echo ""
echo "======================================"
