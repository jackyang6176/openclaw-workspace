#!/usr/bin/env python3
"""台股盤中監控"""
import sys
import os
import json
import time
from datetime import datetime

sys.path.insert(0, '/home/admin/.local/lib/python3.12/site-packages')
from fubon_neo.sdk import FubonSDK, build_rest_client

# Load env
env = {}
for line in open('/home/admin/.env/fubon.env'):
    if '=' in line and not line.startswith('#'):
        k, v = line.strip().split('=', 1)
        env[k] = v.strip()

# Login
sdk = FubonSDK()
lr = sdk.login(env['ACCOUNT'], env['ACCT_PASSWORD'], env['CERT_PATH'], env['CERT_PASSWORD'])
print('Login:', lr.is_success)

token = sdk.exchange_realtime_token()
client = build_rest_client(token)
tech = client.stock.technical

# Load watchlist
with open('/home/admin/.openclaw/workspace/stock-screener/watchlist.json') as f:
    wl = json.load(f)

watchlist = wl.get('watchlist', [])

NOW = datetime.now().strftime('%Y-%m-%d %H:%M')
print(f"=== 台股盤中監控 {NOW} ===")
print(f"{'代碼':<6} {'名稱':<8} {'現價':>8} {'MA5':>8} {'MA20':>8} {'MA20距%':>8} {'三日收斂':<6} {'三日量增':<6}")
print("-" * 70)

signals = []

# Process only first 5 stocks to test
for w in watchlist[:5]:
    code = w['code']
    name = w.get('name', code)[:6]
    
    try:
        time.sleep(0.5)
        ma5_resp = tech.sma(symbol=code, period=5, timeframe='D')
        time.sleep(0.5)
        ma20_resp = tech.sma(symbol=code, period=20, timeframe='D')
        time.sleep(0.5)
        quote = client.stock.intraday.quote(symbol=code)
        
        ma5_list = ma5_resp.get('data', [])
        ma20_list = ma20_resp.get('data', [])
        
        if not ma5_list or not ma20_list:
            print(f"{code:<6} {name:<8} SMA數據不足")
            continue
        
        ma5_data = {d['date']: d['sma'] for d in ma5_list}
        ma20_data = {d['date']: d['sma'] for d in ma20_list}
        all_dates = sorted(set(ma5_data.keys()) & set(ma20_data.keys()))
        
        if len(all_dates) < 25:
            print(f"{code:<6} {name:<8} 共同日期不足{len(all_dates)}")
            continue
        
        latest_date = all_dates[-1]
        ma5_latest = ma5_data[latest_date]
        ma20_latest = ma20_data[latest_date]
        
        if ma20_latest == 0:
            print(f"{code:<6} {name:<8} MA20為0")
            continue
        
        gap_pct = (ma20_latest - ma5_latest) / ma20_latest * 100
        
        # Gap narrowing
        gaps = []
        for date in all_dates:
            if ma20_data[date] > 0:
                gaps.append((ma20_data[date] - ma5_data[date]) / ma20_data[date] * 100)
        
        gap_narrowing = len(gaps) >= 4 and gaps[-1] < gaps[-2] and gaps[-2] < gaps[-3]
        
        # Price
        price = quote.get('lastPrice', quote.get('closePrice', 0))
        
        # Volume
        try:
            time.sleep(0.5)
            hist_resp = client.stock.historical.candles(symbol=code, from_='2026-03-01', to='2026-04-07', timeframe='D')
            vol_data = hist_resp.get('data', [])[:3]
            if len(vol_data) >= 3:
                vol_ok = vol_data[2]['volume'] < vol_data[1]['volume'] < vol_data[0]['volume']
            else:
                vol_ok = False
        except:
            vol_ok = False
        
        # Strategy A
        cond1 = ma5_latest < ma20_latest
        cond2 = 0 < gap_pct < 1.0
        cond3 = gap_narrowing
        cond4 = vol_ok
        signal = cond1 and cond2 and cond3 and cond4
        
        narrowing = "✅" if cond3 else "❌"
        vol = "✅" if cond4 else "❌"
        signal_flag = "📍" if signal else ""
        
        print(f"{code:<6} {name:<8} {price:>8.2f} {ma5_latest:>8.2f} {ma20_latest:>8.2f} {gap_pct:>7.3f}% {narrowing:<6} {vol:<6} {signal_flag}")
        
        if signal:
            signals.append({
                'code': code, 'name': name, 'price': price,
                'ma5': round(ma5_latest, 2), 'ma20': round(ma20_latest, 2),
                'gap_pct': round(gap_pct, 3),
                'gap_seq': [round(g, 3) for g in gaps[-4:]]
            })
        
    except Exception as e:
        print(f"{code:<6} {name:<8} Error: {str(e)[:50]}")

print()
print("=" * 70)
if signals:
    print(f"📍 策略A進場信號 ({len(signals)}檔):")
    for s in signals:
        print(f"  {s['code']} {s['name']} | 現價:{s['price']} | MA5:{s['ma5']} | MA20:{s['ma20']} | MA20距:{s['gap_pct']}%")
        print(f"    三日價差: {s['gap_seq']}")
else:
    print("目前無符合策略A的進場信號")
