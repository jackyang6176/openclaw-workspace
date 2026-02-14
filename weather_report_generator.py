#!/usr/bin/env python3
"""
武陵農場每日氣象報告生成器
執行時間：每天早上7點 (Asia/Shanghai)
"""

import subprocess
import datetime
import os

def get_wuling_weather():
    """獲取武陵農場天氣資訊"""
    # 使用 wttr.in 獲取武陵農場天氣
    # 武陵農場座標: 24.3833,121.3500
    try:
        # 獲取詳細天氣預報
        result = subprocess.run([
            'curl', '-s', 
            'https://wttr.in/24.3833,121.3500?T&lang=zh'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return result.stdout
        else:
            # 備用方案：使用簡化格式
            result = subprocess.run([
                'curl', '-s',
                'https://wttr.in/24.3833,121.3500?format=%l:+%c+%t+%h+%w&lang=zh'
            ], capture_output=True, text=True, timeout=30)
            return result.stdout if result.returncode == 0 else "無法獲取天氣資料"
            
    except Exception as e:
        return f"天氣查詢錯誤: {str(e)}"

def generate_daily_report():
    """生成每日氣象報告"""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    weather_data = get_wuling_weather()
    
    report = f"""# 武陵農場每日氣象報告
**日期**: {today}

## 天氣預報
```
{weather_data}
```

## 旅遊建議
- **穿衣指南**: 根據溫度適時增減衣物
- **攜帶物品**: 雨具、防曬用品、保暖衣物
- **活動建議**: 根據天氣狀況調整戶外活動

---
*本報告由自動化系統生成，資料來源：wttr.in*
"""
    
    # 確保報告目錄存在
    reports_dir = "/home/admin/.openclaw/workspace/wuling_weather/reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    # 保存報告
    report_path = f"{reports_dir}/wuling_weather_{today}.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"武陵農場氣象報告已生成: {report_path}")
    return report_path

if __name__ == "__main__":
    generate_daily_report()