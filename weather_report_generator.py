#!/usr/bin/env python3
"""
武陵農場氣象報告生成器
- 生成 Discord 報告 (Markdown)
- 生成網站報告 (HTML)
"""

import os
import datetime
import subprocess
import json

def get_wuling_weather():
    """獲取武陵農場天氣資料"""
    try:
        # 使用 wttr.in API 獲取天氣資料
        cmd = ['curl', '-s', 'wttr.in/24.3833,121.3500?T']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout if result.returncode == 0 else "無法獲取天氣資料"
    except Exception as e:
        return f"錯誤: {str(e)}"

def generate_markdown_report(weather_data, date_str):
    """生成 Markdown 報告"""
    report = f"""# 武陵農場每日氣象報告
**日期**: {date_str}

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
    return report

def generate_html_report(weather_data, date_str):
    """生成 HTML 報告"""
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>武陵農場氣象報告 - {date_str}</title>
    <link rel="stylesheet" href="../css/style.css">
    <style>
        body {{
            font-family: 'Microsoft JhengHei', sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 3px solid #74b9ff;
        }}
        .header h1 {{
            color: #0984e3;
            font-size: 2.5em;
            margin: 0;
        }}
        .date {{
            color: #666;
            font-size: 1.2em;
            margin-top: 10px;
        }}
        .weather-data {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            font-family: monospace;
            white-space: pre-wrap;
            overflow-x: auto;
        }}
        .advice {{
            background: #e8f4fd;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}
        .advice h3 {{
            color: #0984e3;
            margin-top: 0;
        }}
        .advice ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-style: italic;
        }}
        @media (max-width: 768px) {{
            .container {{
                padding: 15px;
            }}
            .header h1 {{
                font-size: 2em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌤️ 武陵農場氣象報告</h1>
            <div class="date">{date_str}</div>
        </div>
        
        <h2>天氣預報</h2>
        <div class="weather-data">{weather_data.replace('<', '&lt;').replace('>', '&gt;')}</div>
        
        <div class="advice">
            <h3>旅遊建議</h3>
            <ul>
                <li><strong>穿衣指南</strong>: 根據溫度適時增減衣物</li>
                <li><strong>攜帶物品</strong>: 雨具、防曬用品、保暖衣物</li>
                <li><strong>活動建議</strong>: 根據天氣狀況調整戶外活動</li>
            </ul>
        </div>
        
        <div class="footer">
            <p>本服務期間: 2026/02/14 - 2026/02/23 | 資料來源: wttr.in</p>
        </div>
    </div>
</body>
</html>"""
    return html_content

def main():
    """主函數"""
    today = datetime.date.today()
    date_str = today.strftime("%Y-%m-%d")
    
    # 獲取天氣資料
    weather_data = get_wuling_weather()
    
    # 創建報告目錄
    os.makedirs("/home/admin/.openclaw/workspace/wuling_weather/reports", exist_ok=True)
    os.makedirs("/home/admin/.openclaw/workspace/website/travel/wuling-farm/weather", exist_ok=True)
    
    # 生成 Discord 報告 (Markdown)
    markdown_report = generate_markdown_report(weather_data, date_str)
    markdown_path = f"/home/admin/.openclaw/workspace/wuling_weather/reports/wuling_weather_{date_str}.md"
    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(markdown_report)
    
    # 生成網站報告 (HTML)
    html_report = generate_html_report(weather_data, date_str)
    html_path = f"/home/admin/.openclaw/workspace/website/travel/wuling-farm/weather/{date_str}.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    # 創建最新報告的符號連結
    latest_html = "/home/admin/.openclaw/workspace/website/travel/wuling-farm/weather/latest.html"
    if os.path.exists(latest_html):
        os.remove(latest_html)
    os.symlink(f"{date_str}.html", latest_html)
    
    print(f"武陵農場氣象報告已生成:")
    print(f"Discord 報告: {markdown_path}")
    print(f"網站報告: {html_path}")
    print(f"最新報告: http://aiothome.top/travel/wuling-farm/weather/latest.html")

if __name__ == "__main__":
    main()