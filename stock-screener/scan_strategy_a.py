#!/usr/bin/env python3
"""
台股策略A掃描腳本
新策略A（MA5-MA20黃金交叉前夕）：
  1. MA5 < MA20
  2. 兩線價差（MA20-MA5）連三日縮小
  3. 20MA > 5MA 且兩線價差 < 1%
  4. 連三日量增
"""
import sys
import os
sys.path.insert(0, '/home/admin/.openclaw/workspace')
from fubon_sdk_complete.fubon_complete import FubonComplete
import json

def scan_stock(fc, code, name):
    """掃描單一標的"""
    rest = fc.sdk.marketdata.rest_client.stock
    
    # Get intraday quote
    try:
        q = rest.intraday.quote(symbol=code)
    except Exception as e:
        return {'code': code, 'name': name, 'error': f'報價錯誤: {e}'}
    
    if not q or 'lastPrice' not in q:
        return {'code': code, 'name': name, 'error': '無報價'}
    
    d = q
    current_price = d.get('lastPrice') or d.get('closePrice') or d.get('avgPrice')
    change_pct = d.get('changePercent', 0)
    
    # Get SMA data
    sma5_data = fc.get_sma(code, period=5)
    sma20_data = fc.get_sma(code, period=20)
    
    if not sma5_data or not sma20_data:
        return {'code': code, 'name': name, 'error': '無均線數據'}
    
    ma5 = sma5_data[-1]['sma']
    ma20 = sma20_data[-1]['sma']
    
    # Calculate gap
    gap_pct = (ma20 - ma5) / ma20 * 100
    
    # Get historical candles for volume check (only 3 days available)
    try:
        candles = rest.historical.candles(symbol=code, timeframe='D', 
            startDate='2026-03-01', endDate='2026-04-07')
        candle_data = candles.get('data', []) if isinstance(candles, dict) else []
    except:
        candle_data = []
    
    # Check gap narrowing (need last 4 SMA values = 4 days)
    gaps_4d = []
    for i in range(-4, 0):
        if len(sma5_data) >= abs(i) and len(sma20_data) >= abs(i):
            m5 = sma5_data[i]['sma']
            m20 = sma20_data[i]['sma']
            if m20 > 0:
                gaps_4d.append((m20 - m5) / m20 * 100)
    
    gap_narrowing_3d = len(gaps_4d) >= 4 and gaps_4d[-1] < gaps_4d[-2] < gaps_4d[-3]
    
    # Check 3-day volume increase
    vol_3d_inc = False
    vol_data = ""
    if len(candle_data) >= 3:
        v0 = candle_data[0].get('volume', 0)
        v1 = candle_data[1].get('volume', 0)
        v2 = candle_data[2].get('volume', 0)
        vol_3d_inc = v0 > v1 > v2
        vol_data = f"vol: {v0:,}/{v1:,}/{v2:,}"
    
    # Evaluate Strategy A signal
    cond1 = ma5 < ma20
    cond2 = 0 < gap_pct < 1.0
    cond3 = gap_narrowing_3d
    cond4 = vol_3d_inc
    
    signal_score = sum([cond1, cond2, cond3, cond4])
    
    if signal_score >= 3:
        signal = f"⚠️ {signal_score}/4"
    elif signal_score >= 1:
        signal = f"🔹 {signal_score}/4"
    else:
        signal = f"ー {signal_score}/4"
    
    # MA20 distance
    ma20_dist = (current_price - ma20) / ma20 * 100 if current_price else None
    
    return {
        'code': code,
        'name': name,
        'price': current_price,
        'ma5': round(ma5, 2),
        'ma20': round(ma20, 2),
        'gap_pct': round(gap_pct, 3),
        'ma20_dist_pct': round(ma20_dist, 2) if ma20_dist is not None else None,
        'change_pct': round(change_pct, 2),
        'conds': f"MA5<MA20:{cond1}, gap<1%:{cond2}, 收斂3d:{cond3}, 量增3d:{cond4}",
        'signal': signal,
        'vol_data': vol_data,
        'gap_series': [round(g, 3) for g in gaps_4d[-4:]] if gaps_4d else []
    }


def main():
    fc = FubonComplete()
    if not fc.login():
        print("登入失敗")
        return 1
    
    # Load watchlist
    watchlist_path = '/home/admin/.openclaw/workspace/stock-screener/watchlist.json'
    with open(watchlist_path) as f:
        watchlist_data = json.load(f)
    
    stocks = watchlist_data.get('watchlist', [])
    
    results = []
    for stock in stocks:
        code = stock['code']
        name = stock.get('name', code)
        result = scan_stock(fc, code, name)
        results.append(result)
        # Print progress
        if 'error' in result:
            print(f"  {code} {name}: {result['error']}")
        else:
            print(f"  {code} {name}: price={result['price']}, gap={result['gap_pct']}%, signal={result['signal']}")
    
    fc.logout()
    
    # Sort results
    valid = [r for r in results if 'error' not in r]
    errors = [r for r in results if 'error' in r]
    
    # Sort by signal score
    def get_score(r):
        s = r['signal'].split()[0]
        return int(s.replace('⚠️', '').replace('🔹', '').replace('ー', '0'))
    
    valid.sort(key=get_score, reverse=True)
    
    print()
    print("=" * 75)
    print("=== 台股策略A市場掃描 ===")
    print(f"掃描時間: 2026-04-07 13:00 (盤中)")
    print("=" * 75)
    print()
    print(f"{'標的':<8} {'現價':>8} {'MA20距%':>8} {'信號':<6} 備註")
    print("-" * 75)
    
    for r in valid:
        ma20_d = f"{r['ma20_dist_pct']:+.2f}%" if r['ma20_dist_pct'] is not None else "N/A"
        print(f"{r['code']} {r['name']:<4} {r['price']:>8.2f} {ma20_d:>8} {r['signal']:<6} {r['vol_data']}")
    
    print()
    print("--- 詳細條件分析 ---")
    for r in valid:
        print(f"  {r['code']} {r['name']}: MA5={r['ma5']} MA20={r['ma20']} gap={r['gap_pct']}% gaps={r['gap_series']} | {r['conds']}")
    
    if errors:
        print()
        print("--- 讀取失敗 ---")
        for r in errors:
            print(f"  {r['code']} {r['name']}: {r['error']}")
    
    print()
    print("帳戶狀態：（由 main session 填寫）")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
