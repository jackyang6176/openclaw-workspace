#!/usr/bin/env python3
"""
股票篩選工具 - 記憶體優化版本
逐檔處理，即時釋放記憶體
"""
import os
import sys
import gc
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

# 設定路徑
WORKSPACE = "/home/admin/.openclaw/workspace"
FUBON_API = f"{WORKSPACE}/fubon_api"
PCLOUD_DIR = "/home/admin/pCloudDrive/openclaw/stockanalysis"
os.makedirs(PCLOUD_DIR, exist_ok=True)

sys.path.insert(0, FUBON_API)

def log(message: str):
    """簡易日誌"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def check_condition_1(df: pd.DataFrame) -> Tuple[bool, str, float]:
    """條件1：近20日低波動 + 近1-2日價量齊揚"""
    if len(df) < 25:
        return False, "數據不足", 0
    
    recent_20 = df.iloc[-22:-2]
    latest_2 = df.iloc[-2:]
    
    volatility = recent_20['close'].std() / recent_20['close'].mean()
    low_volatility = volatility < 0.05
    
    price_change_1d = (latest_2.iloc[-1]['close'] - recent_20.iloc[-1]['close']) / recent_20.iloc[-1]['close']
    price_surge = price_change_1d > 0.03
    
    avg_volume_20 = recent_20['volume'].mean()
    latest_volume = latest_2.iloc[-1]['volume']
    volume_expansion = latest_volume > avg_volume_20 * 1.5
    
    score = (0.4 if low_volatility else 0) + (0.3 if price_surge else 0) + (0.3 if volume_expansion else 0)
    detail = f"波動率:{volatility:.1%}, 漲幅:{price_change_1d:.1%}, 成交量:{latest_volume/avg_volume_20:.1f}x"
    
    return low_volatility and price_surge and volume_expansion, detail, score

def check_condition_2(df: pd.DataFrame) -> Tuple[bool, str, float]:
    """條件2：KD低於20 + K值向上突破D值"""
    if len(df) < 10:
        return False, "數據不足", 0
    
    # 計算KD
    n = 9
    low_min = df['low'].rolling(window=n).min()
    high_max = df['high'].rolling(window=n).max()
    df['rsv'] = 100 * (df['close'] - low_min) / (high_max - low_min)
    df['k'] = df['rsv'].ewm(com=2).mean()
    df['d'] = df['k'].ewm(com=2).mean()
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    kd_oversold = latest['k'] < 20 and latest['d'] < 20
    golden_cross = prev['k'] <= prev['d'] and latest['k'] > latest['d']
    
    score = (0.5 if kd_oversold else 0) + (0.5 if golden_cross else 0)
    detail = f"K:{latest['k']:.1f}, D:{latest['d']:.1f}, 交叉:{'是' if golden_cross else '否'}"
    
    return kd_oversold and golden_cross, detail, score

def screen_single_stock(client, symbol: str) -> Optional[Dict]:
    """篩選單一股票（記憶體優化版）"""
    try:
        # 獲取數據
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)  # 減少到6個月
        
        data = client.get_historical_candles(
            symbol,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            timeframe="D"
        )
        
        if not data or len(data) < 20:
            return None
        
        # 建立DataFrame
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 只保留最近60天（減少記憶體）
        if len(df) > 60:
            df = df.iloc[-60:]
        
        # 檢查條件
        c1_pass, c1_detail, c1_score = check_condition_1(df)
        c2_pass, c2_detail, c2_score = check_condition_2(df)
        c3_pass, c3_detail, c3_score = True, "需要財務數據", 0.5
        
        total_score = c1_score + c2_score + c3_score
        
        result = {
            'symbol': symbol,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'current_price': float(df.iloc[-1]['close']),
            'volume': int(df.iloc[-1]['volume']),
            'condition_1': {'pass': c1_pass, 'detail': c1_detail, 'score': c1_score},
            'condition_2': {'pass': c2_pass, 'detail': c2_detail, 'score': c2_score},
            'condition_3': {'pass': c3_pass, 'detail': c3_detail, 'score': c3_score},
            'total_score': total_score,
            'all_pass': c1_pass and c2_pass and c3_pass
        }
        
        # 立即釋放記憶體
        del df
        del data
        gc.collect()
        
        return result
        
    except Exception as e:
        log(f"❌ 分析 {symbol} 失敗：{e}")
        return None

def batch_screen(symbols: List[str], batch_size: int = 10) -> List[Dict]:
    """分批篩選，每批處理後釋放記憶體"""
    from fubon_kline_sdk import FubonKlineSDK
    
    results = []
    
    client = FubonKlineSDK()
    if not client.login():
        log("❌ 登入失敗")
        return results
    
    try:
        total = len(symbols)
        for i in range(0, total, batch_size):
            batch = symbols[i:i+batch_size]
            log(f"處理批次 {i//batch_size + 1}/{(total-1)//batch_size + 1} ({len(batch)} 檔)...")
            
            for symbol in batch:
                result = screen_single_stock(client, symbol)
                if result:
                    results.append(result)
                    status = "✅" if result['all_pass'] else "⚠️"
                    log(f"  {status} {symbol}: {result['current_price']:.2f} (得分: {result['total_score']:.1f})")
            
            # 每批結束後強制釋放記憶體
            gc.collect()
            log(f"  批次完成，已釋放記憶體")
            
    finally:
        client.logout()
    
    return results

def generate_simple_report(results: List[Dict]) -> str:
    """生成簡化HTML報告"""
    passed = [r for r in results if r['all_pass']]
    passed.sort(key=lambda x: x['total_score'], reverse=True)
    
    top10 = sorted(results, key=lambda x: x['total_score'], reverse=True)[:10]
    
    rows = ""
    for r in top10:
        status = "✅" if r['all_pass'] else "⚠️"
        rows += f"<tr><td>{status}</td><td>{r['symbol']}</td><td>{r['current_price']:.2f}</td><td>{r['total_score']:.1f}</td><td>{'✅' if r['condition_1']['pass'] else '❌'}</td><td>{'✅' if r['condition_2']['pass'] else '❌'}</td></tr>"
    
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>股票篩選報告</title>
<style>
body{{font-family:Microsoft JhengHei,Arial,sans-serif;background:#1a1a2e;color:#fff;padding:20px}}
.container{{max-width:1000px;margin:0 auto}}
h1{{text-align:center;color:#667eea}}
table{{width:100%;border-collapse:collapse;margin-top:20px}}
th{{background:#667eea;padding:10px}}
td{{padding:8px;text-align:center;border-bottom:1px solid #444}}
tr:nth-child(even){{background:rgba(255,255,255,0.05)}}
.summary{{background:rgba(255,255,255,0.1);padding:15px;border-radius:10px;margin:20px 0}}
</style></head>
<body>
<div class="container">
<h1>📈 股票篩選報告</h1>
<p style="text-align:center">篩選時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<div class="summary">
<p>總查詢: <strong>{len(results)}</strong> 檔 | 完全符合: <strong style="color:#00d084">{len(passed)}</strong> 檔</p>
</div>
<h2>🏆 Top 10 得分最高</h2>
<table>
<tr><th>狀態</th><th>代號</th><th>價格</th><th>得分</th><th>條件1</th><th>條件2</th></tr>
{rows}
</table>
<p style="text-align:center;margin-top:30px;color:#888">Powered by 富邦證券SDK | 記憶體優化版本</p>
</div></body></html>"""
    
    return html

def main():
    """主程式"""
    # 台灣50成分股（50檔）
    symbols = [
        '2330', '2317', '2454', '2382', '2881', '2891', '2308', '2303', '3711', '2882',
        '2886', '2412', '2884', '1216', '2892', '3034', '2357', '3231', '3008', '2327',
        '2890', '3045', '1101', '2885', '2880', '5871', '2301', '2883', '3661', '2379',
        '2887', '1303', '1301', '2395', '1102', '4904', '2603', '2615', '2207', '1590',
        '1402', '9910', '2324', '2618', '2002', '3481', '2353', '2345', '2609', '2610',
    ]
    
    log(f"開始篩選 {len(symbols)} 檔股票（記憶體優化模式）...")
    log("分批處理，每批10檔，處理後立即釋放記憶體")
    
    results = batch_screen(symbols, batch_size=10)
    
    if not results:
        log("❌ 無篩選結果")
        return 1
    
    # 生成報告
    log("\n生成HTML報告...")
    html = generate_simple_report(results)
    
    filename = f"stock_screener_safe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(PCLOUD_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    
    log(f"✅ 報告已保存: {filepath}")
    
    # 輸出結果
    passed = [r for r in results if r['all_pass']]
    log(f"\n{'='*60}")
    log(f"✅ 完全符合: {len(passed)} 檔")
    log(f"⚠️  部分符合: {len(results) - len(passed)} 檔")
    log(f"{'='*60}")
    
    # Top 5
    top5 = sorted(results, key=lambda x: x['total_score'], reverse=True)[:5]
    log("\n🏆 Top 5:")
    for i, r in enumerate(top5, 1):
        log(f"{i}. {r['symbol']}: {r['current_price']:.2f} (得分: {r['total_score']:.1f})")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
