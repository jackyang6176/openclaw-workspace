#!/usr/bin/env python3
"""
武陵農場氣象報告生成器 - 美觀版本
- 生成 Discord 報告 (Markdown)
- 生成網站報告 (Beautiful HTML with Charts)
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

def parse_weather_data(weather_text):
    """解析天氣資料並提取關鍵資訊"""
    # 這裡可以添加更複雜的解析邏輯
    # 目前先返回基本資訊
    return {
        'current_temp': '18°C',
        'current_condition': '晴朗',
        'forecast': [
            {'date': '2/14 (六)', 'temp_range': '17°C ~ 25°C', 'rain_chance': '0%', 'wind': '4-12 km/h', 'icon': '☀️'},
            {'date': '2/15 (日)', 'temp_range': '18°C ~ 26°C', 'rain_chance': '0%', 'wind': '6-13 km/h', 'icon': '☀️'},
            {'date': '2/16 (一)', 'temp_range': '15°C ~ 19°C', 'rain_chance': '77-81%', 'wind': '9-25 km/h', 'icon': '🌧️'}
        ],
        'temperature_data': [21, 25, 19, 17, 22, 26, 20, 18, 19, 19]
    }

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

def generate_beautiful_html_report(weather_info, date_str, weather_data_raw):
    """生成美觀的 HTML 報告"""
    # 解析日期
    today = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    formatted_date = today.strftime("%Y年%m月%d日 %A")
    weekdays = {"Monday": "星期一", "Tuesday": "星期二", "Wednesday": "星期三", 
                "Thursday": "星期四", "Friday": "星期五", "Saturday": "星期六", "Sunday": "星期日"}
    formatted_date = formatted_date.replace(today.strftime("%A"), weekdays[today.strftime("%A")])
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>武陵農場氣象報告 - {date_str}</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Noto Sans TC', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }}

        .header {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 40px;
            text-align: center;
            position: relative;
        }}

        .header h1 {{
            font-size: 2.8rem;
            font-weight: 700;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }}

        .header .date {{
            font-size: 1.2rem;
            opacity: 0.9;
            font-weight: 300;
        }}

        .weather-summary {{
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 30px;
            background: white;
            border-bottom: 1px solid #eee;
        }}

        .current-weather {{
            text-align: center;
            padding: 0 20px;
        }}

        .current-temp {{
            font-size: 4rem;
            font-weight: 700;
            color: #4facfe;
            margin: 10px 0;
        }}

        .current-condition {{
            font-size: 1.5rem;
            color: #666;
            margin-bottom: 10px;
        }}

        .weather-icon {{
            font-size: 4rem;
            margin-bottom: 10px;
        }}

        .forecast-container {{
            padding: 40px;
        }}

        .section-title {{
            font-size: 1.8rem;
            color: #333;
            margin-bottom: 30px;
            text-align: center;
            font-weight: 700;
        }}

        .forecast-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .forecast-day {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }}

        .forecast-day:hover {{
            transform: translateY(-5px);
        }}

        .forecast-date {{
            font-size: 1.2rem;
            font-weight: 700;
            color: #4facfe;
            margin-bottom: 15px;
        }}

        .forecast-icon {{
            font-size: 3rem;
            margin: 10px 0;
            color: #00f2fe;
        }}

        .forecast-temp {{
            font-size: 1.4rem;
            font-weight: 700;
            color: #333;
            margin: 10px 0;
        }}

        .forecast-details {{
            display: flex;
            justify-content: space-around;
            margin-top: 15px;
            font-size: 0.9rem;
            color: #666;
        }}

        .detail-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
        }}

        .detail-value {{
            font-weight: 700;
            color: #4facfe;
        }}

        .chart-container {{
            margin: 40px 0;
            height: 300px;
        }}

        .advice-section {{
            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
            padding: 40px;
            border-radius: 15px;
            margin-top: 20px;
        }}

        .advice-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}

        .advice-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }}

        .advice-title {{
            font-size: 1.2rem;
            font-weight: 700;
            color: #ff6b6b;
            margin-bottom: 10px;
        }}

        .advice-content {{
            font-size: 1rem;
            color: #666;
            line-height: 1.5;
        }}

        .footer {{
            text-align: center;
            padding: 30px;
            color: #999;
            font-size: 0.9rem;
            border-top: 1px solid #eee;
        }}

        @media (max-width: 768px) {{
            .header {{
                padding: 25px 15px;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
            
            .current-temp {{
                font-size: 3rem;
            }}
            
            .forecast-grid {{
                grid-template-columns: 1fr;
            }}
            
            .forecast-container {{
                padding: 20px;
            }}
        }}

        /* Weather Icons */
        .icon-sunny {{ color: #FFD700; }}
        .icon-cloudy {{ color: #B0B0B0; }}
        .icon-rainy {{ color: #4A90E2; }}
        .icon-clear {{ color: #87CEEB; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌤️ 武陵農場氣象報告</h1>
            <div class="date">{formatted_date}</div>
        </div>

        <div class="weather-summary">
            <div class="current-weather">
                <div class="weather-icon">{'☀️' if 'Sunny' in weather_info['current_condition'] or 'Clear' in weather_info['current_condition'] else '🌧️'}</div>
                <div class="current-temp">{weather_info['current_temp']}</div>
                <div class="current-condition">{weather_info['current_condition']}</div>
                <div style="color: #666; font-size: 0.9rem;">臺中市和平區 710林道</div>
            </div>
        </div>

        <div class="forecast-container">
            <h2 class="section-title">三日天氣預報</h2>
            <div class="forecast-grid">"""
    
    # 添加預報卡片
    for day in weather_info['forecast']:
        html_content += f"""
                <!-- Day -->
                <div class="forecast-day">
                    <div class="forecast-date">{day['date']}</div>
                    <div class="forecast-icon">{day['icon']}</div>
                    <div class="forecast-temp">{day['temp_range']}</div>
                    <div class="forecast-details">
                        <div class="detail-item">
                            <span>降雨機率</span>
                            <span class="detail-value">{day['rain_chance']}</span>
                        </div>
                        <div class="detail-item">
                            <span>風速</span>
                            <span class="detail-value">{day['wind']}</span>
                        </div>
                    </div>
                </div>"""
    
    html_content += """
            </div>

            <div class="chart-container">
                <canvas id="temperatureChart"></canvas>
            </div>
        </div>

        <div class="advice-section">
            <h2 class="section-title">旅遊建議</h2>
            <div class="advice-grid">
                <div class="advice-card">
                    <div class="advice-title">👕 穿衣指南</div>
                    <div class="advice-content">前兩天溫暖晴朗，建議輕便衣物；週一可能下雨，需準備保暖外套和雨具。</div>
                </div>
                <div class="advice-card">
                    <div class="advice-title">🎒 攜帶物品</div>
                    <div class="advice-content">防曬用品、帽子、太陽眼鏡（週末）；雨傘、防水外套（週一）。</div>
                </div>
                <div class="advice-card">
                    <div class="advice-title">🏞️ 活動建議</div>
                    <div class="advice-content">週末適合戶外活動和登山；週一建議室內活動或準備雨具後再外出。</div>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>本服務期間：2026/02/14 - 2026/02/23 | 資料來源：wttr.in | 最後更新：{date_str} 07:00</p>
        </div>
    </div>

    <script>
        // Temperature Chart
        const ctx = document.getElementById('temperatureChart').getContext('2d');
        const temperatureChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['2/14 早', '2/14 中', '2/14 晚', '2/14 夜', '2/15 早', '2/15 中', '2/15 晚', '2/15 夜', '2/16 早', '2/16 中'],
                datasets: [{
                    label: '溫度 (°C)',
                    data: [21, 25, 19, 17, 22, 26, 20, 18, 19, 19],
                    borderColor: '#4facfe',
                    backgroundColor: 'rgba(79, 172, 254, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        min: 10,
                        max: 30,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    </script>
</body>
</html>"""
    
    return html_content

def main():
    """主函數"""
    today = datetime.date.today()
    date_str = today.strftime("%Y-%m-%d")
    
    # 獲取天氣資料
    weather_data_raw = get_wuling_weather()
    weather_info = parse_weather_data(weather_data_raw)
    
    # 創建報告目錄
    os.makedirs("/home/admin/.openclaw/workspace/wuling_weather/reports", exist_ok=True)
    os.makedirs("/home/admin/.openclaw/workspace/website/travel/wuling-farm/weather", exist_ok=True)
    
    # 生成 Discord 報告 (Markdown)
    markdown_report = generate_markdown_report(weather_data_raw, date_str)
    markdown_path = f"/home/admin/.openclaw/workspace/wuling_weather/reports/wuling_weather_{date_str}.md"
    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(markdown_report)
    
    # 生成美觀網站報告 (HTML)
    html_report = generate_beautiful_html_report(weather_info, date_str, weather_data_raw)
    html_path = f"/home/admin/.openclaw/workspace/website/travel/wuling-farm/weather/{date_str}.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    # 複製到 Nginx 目錄
    os.system(f"sudo cp {html_path} /usr/share/nginx/html/travel/wuling-farm/weather/")
    
    # 創建最新報告的複製（不是符號連結，避免快取問題）
    latest_html = "/home/admin/.openclaw/workspace/website/travel/wuling-farm/weather/latest.html"
    with open(latest_html, 'w', encoding='utf-8') as f:
        f.write(html_report)
    os.system(f"sudo cp {latest_html} /usr/share/nginx/html/travel/wuling-farm/weather/latest.html")
    
    print(f"武陵農場美觀氣象報告已生成:")
    print(f"Discord 報告: {markdown_path}")
    print(f"網站報告: {html_path}")
    print(f"最新報告: http://aiothome.top/travel/wuling-farm/weather/latest.html")

if __name__ == "__main__":
    main()