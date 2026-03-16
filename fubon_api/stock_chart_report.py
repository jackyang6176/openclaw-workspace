#!/usr/bin/env python3
"""
股市技術線圖分析報告生成器
使用 Apache ECharts 繪製互動式K線圖
"""
import os
import sys
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# 設定路徑
WORKSPACE = "/home/admin/.openclaw/workspace"
FUBON_API = f"{WORKSPACE}/fubon_api"
PCLOUD_DIR = "/home/admin/pCloudDrive/openclaw/stockanalysis"
os.makedirs(PCLOUD_DIR, exist_ok=True)

def log(message: str):
    """簡易日誌"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def get_kline_data(symbol: str, days: int = 60) -> Optional[List[Dict]]:
    """獲取K線數據（使用富邦SDK）"""
    try:
        sys.path.insert(0, FUBON_API)
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
            
            if data and isinstance(data, list):
                # 確保有足夠的數據計算技術指標
                if len(data) > days:
                    data = data[-days:]
                return data
            return data
        finally:
            client.logout()
            
    except Exception as e:
        log(f"❌ 獲取數據失敗：{e}")
        return None

def calculate_ma(data: List[Dict], period: int) -> List[Optional[float]]:
    """計算移動平均線"""
    closes = [d['close'] for d in data]
    ma = []
    for i in range(len(closes)):
        if i < period - 1:
            ma.append(None)
        else:
            ma.append(sum(closes[i-period+1:i+1]) / period)
    return ma

def calculate_rsi(data: List[Dict], period: int = 14) -> List[Optional[float]]:
    """計算RSI"""
    closes = [d['close'] for d in data]
    rsi = [None] * len(closes)
    
    if len(closes) < period + 1:
        return rsi
    
    for i in range(period, len(closes)):
        gains = []
        losses = []
        for j in range(1, period + 1):
            change = closes[i-j+1] - closes[i-j]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            rsi[i] = 100
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_macd(data: List[Dict]) -> tuple:
    """計算MACD"""
    closes = [d['close'] for d in data]
    
    def ema(values, period):
        multiplier = 2 / (period + 1)
        ema_values = [values[0]]
        for price in values[1:]:
            ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
        return ema_values
    
    if len(closes) < 26:
        return [None] * len(closes), [None] * len(closes), [None] * len(closes)
    
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    
    macd_line = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    
    # 訊號線 (MACD的9日EMA)
    signal_line = [None] * 8 + ema(macd_line[8:], 9)
    
    # MACD柱狀圖
    histogram = [m - s if m is not None and s is not None else None 
                 for m, s in zip(macd_line, signal_line)]
    
    return macd_line, signal_line, histogram

def prepare_chart_data(data: List[Dict]) -> Dict:
    """準備圖表數據"""
    dates = [d['date'] for d in data]
    
    # K線數據 [開盤, 收盤, 最低, 最高]
    candle_data = [[d['open'], d['close'], d['low'], d['high']] for d in data]
    
    # 成交量
    volumes = [d['volume'] for d in data]
    
    # 計算移動平均線
    ma5 = calculate_ma(data, 5)
    ma10 = calculate_ma(data, 10)
    ma20 = calculate_ma(data, 20)
    ma60 = calculate_ma(data, 60)
    
    # 計算RSI
    rsi = calculate_rsi(data, 14)
    
    # 計算MACD
    macd_line, signal_line, histogram = calculate_macd(data)
    
    return {
        'dates': dates,
        'candleData': candle_data,
        'volumes': volumes,
        'ma5': ma5,
        'ma10': ma10,
        'ma20': ma20,
        'ma60': ma60,
        'rsi': rsi,
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }

def generate_html(symbol: str, chart_data: Dict, raw_data: List[Dict]) -> str:
    """生成互動式HTML報告"""
    
    # 計算統計資訊
    closes = [d['close'] for d in raw_data]
    last_close = closes[-1]
    first_close = closes[0]
    total_change = ((last_close - first_close) / first_close) * 100
    max_price = max(d['high'] for d in raw_data)
    min_price = min(d['low'] for d in raw_data)
    avg_volume = sum(d['volume'] for d in raw_data) / len(raw_data)
    
    # 判斷趨勢
    ma20 = chart_data['ma20'][-1] if chart_data['ma20'][-1] else last_close
    trend = "上漲📈" if last_close > ma20 else "下跌📉" if last_close < ma20 else "盤整➡️"
    
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} 技術分析圖表 - Powered by Apache ECharts</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Microsoft JhengHei', 'PingFang TC', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid #667eea;
            margin-bottom: 30px;
        }}
        
        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .subtitle {{
            color: #888;
            font-size: 1.1em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        }}
        
        .stat-label {{
            color: #888;
            font-size: 0.9em;
            margin-bottom: 8px;
        }}
        
        .stat-value {{
            font-size: 1.8em;
            font-weight: bold;
        }}
        
        .positive {{ color: #00d084; }}
        .negative {{ color: #ff4757; }}
        .neutral {{ color: #ffa502; }}
        
        .chart-container {{
            background: rgba(255,255,255,0.03);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .chart-title {{
            font-size: 1.3em;
            margin-bottom: 15px;
            color: #667eea;
            border-left: 4px solid #667eea;
            padding-left: 10px;
        }}
        
        #mainChart, #rsiChart, #macdChart {{
            width: 100%;
            height: 500px;
        }}
        
        #rsiChart, #macdChart {{
            height: 250px;
        }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            border-top: 1px solid rgba(255,255,255,0.1);
            margin-top: 30px;
        }}
        
        .loading {{
            text-align: center;
            padding: 50px;
            color: #667eea;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📈 {symbol} 技術分析圖表</h1>
            <p class="subtitle">Apache ECharts 互動式股市分析 | 生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">目前價格</div>
                <div class="stat-value">{last_close:.2f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">區間漲跌</div>
                <div class="stat-value {'positive' if total_change > 0 else 'negative'}">{total_change:+.2f}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">最高價</div>
                <div class="stat-value positive">{max_price:.2f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">最低價</div>
                <div class="stat-value negative">{min_price:.2f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">趨勢判斷</div>
                <div class="stat-value neutral">{trend}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">平均成交量</div>
                <div class="stat-value">{avg_volume/1000000:.1f}M</div>
            </div>
        </div>
        
        <div class="chart-container">
            <div class="chart-title">K線圖與移動平均線</div>
            <div id="mainChart"></div>
        </div>
        
        <div class="chart-container">
            <div class="chart-title">RSI 相對強弱指標</div>
            <div id="rsiChart"></div>
        </div>
        
        <div class="chart-container">
            <div class="chart-title">MACD 指標</div>
            <div id="macdChart"></div>
        </div>
        
        <div class="footer">
            <p>Powered by 富邦證券SDK + Apache ECharts + Kronos AI</p>
            <p>數據僅供參考，投資有風險，決策需謹慎</p>
        </div>
    </div>
    
    <script>
        // 圖表數據
        const chartData = {json.dumps(chart_data, ensure_ascii=False)};
        
        // 顏色配置
        const colors = {{
            up: '#00d084',
            down: '#ff4757',
            ma5: '#e74c3c',
            ma10: '#f39c12',
            ma20: '#3498db',
            ma60: '#9b59b6'
        }};
        
        // 計算漲跌顏色
        const data0 = chartData.candleData.map(item => {{
            return {{
                value: item,
                itemStyle: {{
                    color: item[1] > item[0] ? colors.up : colors.down,
                    borderColor: item[1] > item[0] ? colors.up : colors.down
                }}
            }};
        }});
        
        // 主圖表 - K線 + MA
        const mainChart = echarts.init(document.getElementById('mainChart'));
        const mainOption = {{
            backgroundColor: 'transparent',
            tooltip: {{
                trigger: 'axis',
                axisPointer: {{ type: 'cross' }},
                backgroundColor: 'rgba(0,0,0,0.8)',
                borderColor: '#667eea',
                textStyle: {{ color: '#fff' }}
            }},
            legend: {{
                data: ['K線', 'MA5', 'MA10', 'MA20', 'MA60'],
                textStyle: {{ color: '#fff' }},
                top: 10
            }},
            grid: {{
                left: '10%',
                right: '10%',
                bottom: '15%'
            }},
            xAxis: {{
                type: 'category',
                data: chartData.dates,
                scale: true,
                boundaryGap: false,
                axisLine: {{ lineStyle: {{ color: '#666' }} }},
                axisLabel: {{ color: '#888' }},
                splitLine: {{ show: false }}
            }},
            yAxis: {{
                scale: true,
                axisLine: {{ lineStyle: {{ color: '#666' }} }},
                axisLabel: {{ color: '#888' }},
                splitLine: {{ lineStyle: {{ color: 'rgba(255,255,255,0.1)' }} }}
            }},
            dataZoom: [
                {{
                    type: 'inside',
                    start: 50,
                    end: 100
                }},
                {{
                    show: true,
                    type: 'slider',
                    top: '90%',
                    start: 50,
                    end: 100,
                    textStyle: {{ color: '#888' }}
                }}
            ],
            series: [
                {{
                    name: 'K線',
                    type: 'candlestick',
                    data: data0,
                    itemStyle: {{
                        color: colors.up,
                        color0: colors.down,
                        borderColor: colors.up,
                        borderColor0: colors.down
                    }}
                }},
                {{
                    name: 'MA5',
                    type: 'line',
                    data: chartData.ma5,
                    smooth: true,
                    lineStyle: {{ color: colors.ma5, width: 1 }},
                    symbol: 'none'
                }},
                {{
                    name: 'MA10',
                    type: 'line',
                    data: chartData.ma10,
                    smooth: true,
                    lineStyle: {{ color: colors.ma10, width: 1 }},
                    symbol: 'none'
                }},
                {{
                    name: 'MA20',
                    type: 'line',
                    data: chartData.ma20,
                    smooth: true,
                    lineStyle: {{ color: colors.ma20, width: 1.5 }},
                    symbol: 'none'
                }},
                {{
                    name: 'MA60',
                    type: 'line',
                    data: chartData.ma60,
                    smooth: true,
                    lineStyle: {{ color: colors.ma60, width: 2 }},
                    symbol: 'none'
                }}
            ]
        }};
        mainChart.setOption(mainOption);
        
        // RSI圖表
        const rsiChart = echarts.init(document.getElementById('rsiChart'));
        const rsiOption = {{
            backgroundColor: 'transparent',
            tooltip: {{
                trigger: 'axis',
                backgroundColor: 'rgba(0,0,0,0.8)',
                borderColor: '#667eea',
                textStyle: {{ color: '#fff' }}
            }},
            grid: {{
                left: '10%',
                right: '10%',
                bottom: '15%',
                top: '15%'
            }},
            xAxis: {{
                type: 'category',
                data: chartData.dates,
                show: false
            }},
            yAxis: {{
                min: 0,
                max: 100,
                axisLine: {{ lineStyle: {{ color: '#666' }} }},
                axisLabel: {{ color: '#888' }},
                splitLine: {{ lineStyle: {{ color: 'rgba(255,255,255,0.1)' }} }}
            }},
            series: [{{
                name: 'RSI',
                type: 'line',
                data: chartData.rsi,
                smooth: true,
                lineStyle: {{ color: '#f39c12', width: 2 }},
                areaStyle: {{
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        {{ offset: 0, color: 'rgba(243, 156, 18, 0.3)' }},
                        {{ offset: 1, color: 'rgba(243, 156, 18, 0.05)' }}
                    ])
                }},
                markLine: {{
                    data: [
                        {{ yAxis: 70, lineStyle: {{ color: '#ff4757', type: 'dashed' }}, label: {{ formatter: '超買 70', color: '#ff4757' }} }},
                        {{ yAxis: 30, lineStyle: {{ color: '#00d084', type: 'dashed' }}, label: {{ formatter: '超賣 30', color: '#00d084' }} }}
                    ]
                }}
            }}]
        }};
        rsiChart.setOption(rsiOption);
        
        // MACD圖表
        const macdChart = echarts.init(document.getElementById('macdChart'));
        const macdOption = {{
            backgroundColor: 'transparent',
            tooltip: {{
                trigger: 'axis',
                backgroundColor: 'rgba(0,0,0,0.8)',
                borderColor: '#667eea',
                textStyle: {{ color: '#fff' }}
            }},
            legend: {{
                data: ['MACD', '訊號線', '柱狀圖'],
                textStyle: {{ color: '#fff' }},
                top: 5
            }},
            grid: {{
                left: '10%',
                right: '10%',
                bottom: '15%',
                top: '20%'
            }},
            xAxis: {{
                type: 'category',
                data: chartData.dates,
                axisLine: {{ lineStyle: {{ color: '#666' }} }},
                axisLabel: {{ color: '#888' }},
                splitLine: {{ show: false }}
            }},
            yAxis: {{
                axisLine: {{ lineStyle: {{ color: '#666' }} }},
                axisLabel: {{ color: '#888' }},
                splitLine: {{ lineStyle: {{ color: 'rgba(255,255,255,0.1)' }} }}
            }},
            series: [
                {{
                    name: 'MACD',
                    type: 'line',
                    data: chartData.macd,
                    smooth: true,
                    lineStyle: {{ color: '#3498db', width: 2 }},
                    symbol: 'none'
                }},
                {{
                    name: '訊號線',
                    type: 'line',
                    data: chartData.signal,
                    smooth: true,
                    lineStyle: {{ color: '#e74c3c', width: 2 }},
                    symbol: 'none'
                }},
                {{
                    name: '柱狀圖',
                    type: 'bar',
                    data: chartData.histogram.map((val, idx) => ({{
                        value: val,
                        itemStyle: {{
                            color: val > 0 ? '#00d084' : '#ff4757'
                        }}
                    }}))
                }}
            ]
        }};
        macdChart.setOption(macdOption);
        
        // 響應式調整
        window.addEventListener('resize', () => {{
            mainChart.resize();
            rsiChart.resize();
            macdChart.resize();
        }});
    </script>
</body>
</html>"""
    
    return html

def save_report(html_content: str, symbol: str) -> str:
    """保存報告到pCloudDrive"""
    filename = f"stock_chart_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(PCLOUD_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        log(f"✅ 報告已保存：{filepath}")
        return filepath
    except Exception as e:
        log(f"❌ 保存失敗：{e}")
        return None

def main():
    """主程式"""
    if len(sys.argv) < 2:
        print("""
股市技術線圖分析報告生成器

使用方法：
    python3 stock_chart_report.py <股票代號> [天數]

範例：
    python3 stock_chart_report.py 00887
    python3 stock_chart_report.py 00655L 60
    python3 stock_chart_report.py 00882 90
""")
        return 1
    
    symbol = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    
    log(f"開始生成 {symbol} 的技術線圖報告...")
    
    # 獲取K線數據
    log(f"獲取最近 {days} 天K線數據...")
    data = get_kline_data(symbol, days)
    
    if not data or len(data) < 20:
        log("❌ 無法獲取足夠的K線數據")
        return 1
    
    log(f"✅ 成功獲取 {len(data)} 筆數據")
    
    # 準備圖表數據
    log("計算技術指標...")
    chart_data = prepare_chart_data(data)
    
    # 生成HTML
    log("生成互動式HTML報告...")
    html = generate_html(symbol, chart_data, data)
    
    # 保存
    filepath = save_report(html, symbol)
    
    if filepath:
        log(f"\n✅ 完成！報告位置：{filepath}")
        return 0
    else:
        log("❌ 保存失敗")
        return 1

if __name__ == "__main__":
    sys.exit(main())
