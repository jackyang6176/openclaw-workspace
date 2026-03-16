#!/usr/bin/env python3
"""
K線數據分析工具 - Kronos Small 版本
使用 Kronos AI 模型分析K線數據並生成網頁報告
"""
import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# 添加 Kronos 模型路徑
KRONOS_PATH = '/home/admin/.openclaw/workspace/Kronos'
sys.path.insert(0, KRONOS_PATH)

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
    """獲取K線數據（使用富邦SDK）"""
    try:
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

def analyze_with_kronos(symbol: str, data: List[Dict]) -> Dict:
    """使用 Kronos Small 模型分析K線數據"""
    
    try:
        from model import Kronos, KronosTokenizer, KronosPredictor
        
        log("📥 加載 Kronos Small 模型...")
        
        # 加載 tokenizer
        tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
        
        # 加載模型
        model = Kronos.from_pretrained("NeoQuasar/Kronos-small")
        
        # 初始化預測器
        predictor = KronosPredictor(model, tokenizer, max_context=512)
        
        log("✅ Kronos 模型加載成功")
        
        # 準備數據
        df = pd.DataFrame(data)
        df['timestamps'] = pd.to_datetime(df['date'])
        
        # 轉換為5分鐘K線格式（Kronos需要）
        # 由於我們有日K，模擬成5分鐘K線
        lookback = min(60, len(df))  # Kronos 使用較短的lookback
        x_df = df.iloc[-lookback:][['open', 'high', 'low', 'close', 'volume']].copy()
        x_timestamp = df['timestamps'].iloc[-lookback:].reset_index(drop=True)
        
        # 預測時間戳（預測未來12個時間單位，約1小時）
        last_time = x_timestamp.iloc[-1]
        pred_len = 12
        y_timestamp = pd.date_range(
            start=last_time + pd.Timedelta(hours=1),
            periods=pred_len,
            freq='H'
        )
        
        log("🔮 使用 Kronos 生成預測...")
        
        # 生成預測
        pred_df = predictor.predict(
            df=x_df,
            x_timestamp=x_timestamp,
            y_timestamp=pd.Series(y_timestamp),
            pred_len=pred_len,
            T=1.0,
            top_p=0.9,
            sample_count=1,
            verbose=False
        )
        
        log("✅ Kronos 預測完成")
        
        # 計算技術指標
        closes = df['close'].values
        last_close = closes[-1]
        
        # 預測價格
        pred_close = pred_df['close'].mean()
        pred_short = pred_df['close'].iloc[:4].mean()
        pred_mid = pred_df['close'].iloc[:8].mean()
        
        # 計算預期漲跌
        short_change = (pred_short - last_close) / last_close * 100
        mid_change = (pred_mid - last_close) / last_close * 100
        
        # 生成信號
        if short_change > 1:
            signal = "BUY"
            confidence = min(abs(short_change) * 20, 95)
        elif short_change < -1:
            signal = "SELL"
            confidence = min(abs(short_change) * 20, 95)
        else:
            signal = "HOLD"
            confidence = 50
        
        # 目標價和停損
        target_price = last_close * (1 + short_change/100 * 1.5)
        stop_loss = last_close * 0.98 if signal == "BUY" else last_close * 1.02
        
        return {
            'symbol': symbol,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_price': last_close,
            'kronos_prediction': {
                'short_term': pred_short,
                'mid_term': pred_mid,
                'long_term': pred_close
            },
            'signals': {
                'signal': signal,
                'confidence': confidence,
                'target_price': target_price,
                'stop_loss': stop_loss,
                'short_term_change': short_change,
                'mid_term_change': mid_change
            },
            'analysis_text': f"""
【Kronos AI 技術分析】

1. Kronos 模型預測：
   - 短期預測（4小時）：{pred_short:.2f}
   - 中期預測（8小時）：{pred_mid:.2f}
   - 整體預測平均：{pred_close:.2f}

2. 預期漲跌：
   - 短期：{short_change:+.2f}%
   - 中期：{mid_change:+.2f}%

3. 交易信號：
   - 信號：{signal}
   - 置信度：{confidence:.1f}%
   - 目標價：{target_price:.2f}
   - 停損價：{stop_loss:.2f}

4. 綜合評估：
   - Kronos AI 模型預測{'看漲' if short_change > 0 else '看跌'}
   - 建議操作：{'買入' if signal == 'BUY' else '賣出' if signal == 'SELL' else '觀望'}
""",
            'kline_data': data,
            'prediction_data': pred_df.to_dict('records') if hasattr(pred_df, 'to_dict') else []
        }
        
    except Exception as e:
        log(f"❌ Kronos 分析失敗：{e}")
        import traceback
        log(traceback.format_exc())
        
        # 使用備選分析
        return analyze_fallback(symbol, data)

def analyze_fallback(symbol: str, data: List[Dict]) -> Dict:
    """備選分析（當Kronos不可用時）"""
    log("⚠️  使用備選技術分析...")
    
    closes = [d['close'] for d in data]
    last_close = closes[-1]
    first_close = closes[0]
    
    total_change = (last_close - first_close) / first_close * 100
    
    # 簡單趨勢判斷
    if total_change > 5:
        signal = "BUY"
        confidence = 70
    elif total_change < -5:
        signal = "SELL"
        confidence = 70
    else:
        signal = "HOLD"
        confidence = 50
    
    return {
        'symbol': symbol,
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'current_price': last_close,
        'signals': {
            'signal': signal,
            'confidence': confidence,
            'target_price': last_close * 1.05,
            'stop_loss': last_close * 0.95,
            'short_term_change': total_change / 5,
            'mid_term_change': total_change
        },
        'analysis_text': f"""
【技術分析摘要】（備選模式）

1. 價格趨勢：
   - 目前價格：{last_close:.2f}
   - 區間漲跌：{total_change:+.2f}%

2. 交易信號：
   - 信號：{signal}
   - 置信度：{confidence:.1f}%

3. 綜合評估：
   - 趨勢：{'上漲' if total_change > 0 else '下跌'}
   - 建議操作：{'買入' if signal == 'BUY' else '賣出' if signal == 'SELL' else '觀望'}

（注意：此為備選分析，Kronos AI 模型未成功加載）
""",
        'kline_data': data,
        'prediction_data': []
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
    
    # Kronos標記
    kronos_badge = "<span class='kronos-badge'>🤖 Kronos AI</span>" if 'kronos_prediction' in analysis else ""
    
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} K線技術分析報告 - Kronos AI</title>
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
        
        .kronos-badge {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            margin-left: 10px;
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
        
        .metric-card .positive {{ color: #28a745; }}
        .metric-card .negative {{ color: #dc3545; }}
        
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
        
        tr:nth-child(even) {{ background: #f8f9fa; }}
        
        .positive {{ color: #28a745; font-weight: bold; }}
        .negative {{ color: #dc3545; font-weight: bold; }}
        
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
        <h1>📈 {symbol} K線技術分析報告 {kronos_badge}</h1>
        <p class="subtitle">分析時間：{analysis['analysis_date']}</p>
        
        <div class="summary">
            <h2>📊 綜合評估</h2>
            <p>目前價格：<strong>{analysis['current_price']:.2f}</strong></p>
            <p>AI信號：<strong>{analysis['signals']['signal']}</strong></p>
            <p>置信度：<strong>{analysis['signals']['confidence']:.1f}%</strong></p>
        </div>
        
        <div class="metrics">
            <div class="metric-card">
                <h3>目標價</h3>
                <div class="value">{analysis['signals']['target_price']:.2f}</div>
            </div>
            <div class="metric-card">
                <h3>停損價</h3>
                <div class="value">{analysis['signals']['stop_loss']:.2f}</div>
            </div>
            <div class="metric-card">
                <h3>短期預期</h3>
                <div class="value {'positive' if analysis['signals']['short_term_change'] > 0 else 'negative'}">{analysis['signals']['short_term_change']:+.2f}%</div>
            </div>
            <div class="metric-card">
                <h3>中期預期</h3>
                <div class="value {'positive' if analysis['signals']['mid_term_change'] > 0 else 'negative'}">{analysis['signals']['mid_term_change']:+.2f}%</div>
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
            <p>Powered by 富邦證券SDK + Kronos Small AI模型</p>
        </div>
    </div>
</body>
</html>"""
    
    return html

def save_report(html_content: str, symbol: str) -> str:
    """保存報告到pCloudDrive"""
    filename = f"kronos_analysis_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(PCLOUD_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        log(f"✅ 報告已保存：{filepath}")
        return filepath
    except Exception as e:
        log(f"❌ pCloudDrive保存失敗：{e}")
        local_path = os.path.join(LOG_DIR, filename)
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        log(f"✅ 報告已保存到本地：{local_path}")
        return local_path

def main():
    """主程式"""
    symbol = sys.argv[1] if len(sys.argv) > 1 else "00887"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    
    log(f"開始使用 Kronos AI 分析 {symbol} 的K線數據...")
    
    # 獲取K線數據
    log("獲取K線數據...")
    data = get_kline_data(symbol, days)
    
    if not data:
        log("❌ 無法獲取K線數據")
        return 1
    
    log(f"✅ 成功獲取 {len(data)} 筆數據")
    
    # 使用Kronos分析
    log("使用 Kronos Small AI 模型進行分析...")
    analysis = analyze_with_kronos(symbol, data)
    
    # 生成HTML報告
    log("生成HTML報告...")
    html = generate_html_report(analysis)
    
    # 保存報告
    filepath = save_report(html, symbol)
    
    log(f"\n✅ Kronos AI 分析完成！")
    log(f"報告位置：{filepath}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
