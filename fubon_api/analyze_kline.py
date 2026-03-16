#!/usr/bin/env python3
"""
K線數據分析工具
使用AI模型分析K線數據並生成網頁報告
"""
import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# 設定路徑
LOG_DIR = "/home/admin/.openclaw/workspace/fubon_api/logs"
PCLOUD_DIR = "/home/admin/pCloudDrive/openclaw"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(PCLOUD_DIR, exist_ok=True)

def log(message: str):
    """簡易日誌"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def get_kline_data(symbol: str, days: int = 20) -> Optional[List[Dict]]:
    """獲取K線數據"""
    try:
        # 使用富邦SDK獲取數據
        sys.path.insert(0, '/home/admin/.openclaw/workspace/fubon_api')
        from fubon_kline_sdk import FubonKlineSDK
        
        client = FubonKlineSDK()
        
        if not client.login():
            return None
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days * 2)
            
            data = client.get_historical_candles(
                symbol,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                timeframe="D"
            )
            
            if data and isinstance(data, list) and len(data) > days:
                data = data[-days:]
            
            return data
        finally:
            client.logout()
            
    except Exception as e:
        log(f"❌ 獲取數據失敗：{e}")
        return None

def analyze_with_ai(symbol: str, data: List[Dict]) -> Dict:
    """使用AI模型分析K線數據"""
    
    # 計算技術指標
    closes = [d['close'] for d in data]
    highs = [d['high'] for d in data]
    lows = [d['low'] for d in data]
    volumes = [d['volume'] for d in data]
    
    # 計算移動平均線
    def sma(values, period):
        if len(values) < period:
            return sum(values) / len(values)
        return sum(values[-period:]) / period
    
    sma5 = sma(closes, 5)
    sma10 = sma(closes, 10)
    sma20 = sma(closes, 20)
    
    # 計算RSI
    def rsi(prices, period=14):
        if len(prices) < period + 1:
            return 50
        gains = []
        losses = []
        for i in range(1, period + 1):
            change = prices[-i] - prices[-i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    rsi_value = rsi(closes)
    
    # 計算MACD
    def ema(prices, period):
        multiplier = 2 / (period + 1)
        ema_values = [prices[0]]
        for price in prices[1:]:
            ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
        return ema_values[-1]
    
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd_line = ema12 - ema26
    signal_line = ema([ema12 - ema26], 9) if len(closes) >= 9 else macd_line
    macd_histogram = macd_line - signal_line
    
    # 趨勢分析
    first_close = closes[0]
    last_close = closes[-1]
    total_change = last_close - first_close
    total_change_pct = (total_change / first_close) * 100
    
    # 判斷趨勢
    trend = "上漲" if last_close > sma20 else "下跌" if last_close < sma20 else "盤整"
    
    # 支撐與壓力
    support = min(lows[-5:])
    resistance = max(highs[-5:])
    
    # 成交量分析
    avg_volume = sum(volumes) / len(volumes)
    recent_volume = sum(volumes[-3:]) / 3
    volume_trend = "放量" if recent_volume > avg_volume * 1.2 else "縮量" if recent_volume < avg_volume * 0.8 else "正常"
    
    # 生成AI分析文字
    analysis_text = f"""
【技術分析摘要】

1. 價格趨勢：
   - 目前價格：{last_close:.2f}
   - 20日趨勢：{trend}
   - 區間漲跌：{total_change:+.2f} ({total_change_pct:+.2f}%)

2. 移動平均線：
   - MA5：{sma5:.2f}
   - MA10：{sma10:.2f}
   - MA20：{sma20:.2f}
   - 目前價格{'高於' if last_close > sma20 else '低於'}MA20

3. 技術指標：
   - RSI(14)：{rsi_value:.2f} ({'超買' if rsi_value > 70 else '超賣' if rsi_value < 30 else '中性'})
   - MACD：{macd_line:.4f}
   - 訊號線：{signal_line:.4f}
   - 柱狀圖：{macd_histogram:.4f} ({'多頭' if macd_histogram > 0 else '空頭'})

4. 支撐與壓力：
   - 近期支撐：{support:.2f}
   - 近期壓力：{resistance:.2f}

5. 成交量分析：
   - 平均成交量：{avg_volume:,.0f}
   - 近期趨勢：{volume_trend}

6. 綜合評估：
   - 短線趨勢：{'偏多' if last_close > sma5 and macd_histogram > 0 else '偏空' if last_close < sma5 and macd_histogram < 0 else '觀望'}
   - 中線趨勢：{'偏多' if last_close > sma20 else '偏空'}
   - 建議操作：{'考慮買入' if rsi_value < 40 and macd_histogram > 0 else '考慮賣出' if rsi_value > 70 and macd_histogram < 0 else '觀望'}
"""
    
    return {
        'symbol': symbol,
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'current_price': last_close,
        'trend': trend,
        'total_change': total_change,
        'total_change_pct': total_change_pct,
        'sma5': sma5,
        'sma10': sma10,
        'sma20': sma20,
        'rsi': rsi_value,
        'macd': macd_line,
        'signal': signal_line,
        'macd_histogram': macd_histogram,
        'support': support,
        'resistance': resistance,
        'avg_volume': avg_volume,
        'volume_trend': volume_trend,
        'analysis_text': analysis_text,
        'kline_data': data
    }

def generate_html_report(analysis: Dict) -> str:
    """生成HTML報告"""
    
    symbol = analysis['symbol']
    data = analysis['kline_data']
    
    # 生成K線表格
    table_rows = ""
    for item in data:
        change_class = "positive" if item.get('change', 0) >= 0 else "negative"
        change_str = f"{item.get('change', 0):+.2f}" if item.get('change', 0) != 0 else "-"
        
        table_rows += f"""
        <tr>
            <td>{item['date']}</td>
            <td>{item['open']:.2f}</td>
            <td>{item['high']:.2f}</td>
            <td>{item['low']:.2f}</td>
            <td>{item['close']:.2f}</td>
            <td class="{change_class}">{change_str}</td>
            <td>{item['volume']:,}</td>
        </tr>
        """
    
    # 生成HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} K線技術分析報告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Microsoft JhengHei', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
        }}
        
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2em;
        }}
        
        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }}
        
        .summary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        
        .summary h2 {{
            margin-bottom: 15px;
        }}
        
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border-left: 4px solid #667eea;
        }}
        
        .metric-card h3 {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
        }}
        
        .metric-card .value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #333;
        }}
        
        .metric-card .positive {{
            color: #28a745;
        }}
        
        .metric-card .negative {{
            color: #dc3545;
        }}
        
        .analysis {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            white-space: pre-wrap;
            font-family: monospace;
            line-height: 1.6;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: center;
        }}
        
        td {{
            padding: 10px;
            text-align: center;
            border-bottom: 1px solid #ddd;
        }}
        
        tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        
        .positive {{
            color: #28a745;
            font-weight: bold;
        }}
        
        .negative {{
            color: #dc3545;
            font-weight: bold;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 {symbol} K線技術分析報告</h1>
        <p class="subtitle">分析時間：{analysis['analysis_date']}</p>
        
        <div class="summary">
            <h2>📊 綜合評估</h2>
            <p>目前價格：<strong>{analysis['current_price']:.2f}</strong></p>
            <p>20日趨勢：<strong>{analysis['trend']}</strong></p>
            <p>區間漲跌：<strong class="{'positive' if analysis['total_change'] >= 0 else 'negative'}">{analysis['total_change']:+.2f} ({analysis['total_change_pct']:+.2f}%)</strong></p>
        </div>
        
        <div class="metrics">
            <div class="metric-card">
                <h3>RSI (14)</h3>
                <div class="value {'positive' if analysis['rsi'] > 60 else 'negative' if analysis['rsi'] < 40 else ''}">{analysis['rsi']:.2f}</div>
            </div>
            <div class="metric-card">
                <h3>MACD</h3>
                <div class="value {'positive' if analysis['macd_histogram'] > 0 else 'negative'}">{analysis['macd_histogram']:.4f}</div>
            </div>
            <div class="metric-card">
                <h3>MA5</h3>
                <div class="value">{analysis['sma5']:.2f}</div>
            </div>
            <div class="metric-card">
                <h3>MA20</h3>
                <div class="value">{analysis['sma20']:.2f}</div>
            </div>
            <div class="metric-card">
                <h3>支撐位</h3>
                <div class="value">{analysis['support']:.2f}</div>
            </div>
            <div class="metric-card">
                <h3>壓力位</h3>
                <div class="value">{analysis['resistance']:.2f}</div>
            </div>
        </div>
        
        <h2>🤖 AI技術分析</h2>
        <div class="analysis">{analysis['analysis_text']}</div>
        
        <h2>📋 K線數據明細（最近20個交易日）</h2>
        <table>
            <thead>
                <tr>
                    <th>日期</th>
                    <th>開盤</th>
                    <th>最高</th>
                    <th>最低</th>
                    <th>收盤</th>
                    <th>漲跌</th>
                    <th>成交量</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        
        <div class="footer">
            <p>報告生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Powered by 富邦證券SDK + AI技術分析</p>
        </div>
    </div>
</body>
</html>"""
    
    return html

def save_report(html_content: str, symbol: str) -> str:
    """保存報告到pCloudDrive"""
    filename = f"kline_analysis_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(PCLOUD_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        log(f"✅ 報告已保存：{filepath}")
        return filepath
    except Exception as e:
        log(f"❌ 保存失敗：{e}")
        # 如果pCloudDrive不可用，保存到本地
        local_path = os.path.join(LOG_DIR, filename)
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        log(f"✅ 報告已保存到本地：{local_path}")
        return local_path

def main():
    """主程式"""
    symbol = sys.argv[1] if len(sys.argv) > 1 else "00887"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    
    log(f"開始分析 {symbol} 的K線數據...")
    
    # 獲取K線數據
    log("獲取K線數據...")
    data = get_kline_data(symbol, days)
    
    if not data:
        log("❌ 無法獲取K線數據")
        return 1
    
    log(f"✅ 成功獲取 {len(data)} 筆數據")
    
    # 分析數據
    log("進行AI技術分析...")
    analysis = analyze_with_ai(symbol, data)
    
    # 生成HTML報告
    log("生成HTML報告...")
    html = generate_html_report(analysis)
    
    # 保存報告
    filepath = save_report(html, symbol)
    
    log(f"\n✅ 分析完成！")
    log(f"報告位置：{filepath}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
