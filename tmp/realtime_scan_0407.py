#!/usr/bin/env python3
"""
台股即時監控 - 策略A市場掃描
2026-04-07 11:06 AM
"""
import os, sys, datetime, json

WORKSPACE = "/home/admin/.openclaw/workspace"
SCREENER_DIR = f"{WORKSPACE}/stock-screener"
FUBON_API_DIR = f"{WORKSPACE}/fubon_api"
sys.path.insert(0, FUBON_API_DIR)

from fubon_kline_sdk import FubonKlineSDK

NOW = datetime.datetime.now()
NOW_STR = NOW.strftime('%Y-%m-%d %H:%M')
TS_STR  = NOW.strftime('%H:%M:%S')

print(f"\n[{TS_STR}] === 台股策略A市場掃描 {NOW_STR} ===\n")

# 登入
kline_sdk = FubonKlineSDK()
if not kline_sdk.login():
    print("❌ 登入失敗"); sys.exit(1)
print("✅ 富邦登入成功\n")

# 讀取 watchlist
wl_path = f"{SCREENER_DIR}/watchlist.json"
with open(wl_path) as f:
    wl_data = json.load(f)

watchlist = wl_data.get('watchlist', [])
holdings = wl_data.get('holdings', {})

# 策略A候選
strategy_a_stocks = [w for w in watchlist 
    if '策略A' in w.get('strategy', '')
    or '新策略A' in w.get('strategy', '')]
print(f"策略A候選標的：{len(strategy_a_stocks)} 檔\n")

results = []

def ma_at(data, idx):
    """MA ending at day idx (0=oldest, n-1=newest complete day)"""
    n = len(data)
    start5 = max(0, idx - 4)
    end5 = idx + 1
    start20 = max(0, idx - 19)
    end20 = idx + 1
    m5 = sum(data[start5:end5]) / min(5, end5 - start5)
    m20 = sum(data[start20:end20]) / min(20, end20 - start20)
    return m5, m20

for stock in strategy_a_stocks:
    code = stock['code']
    name = stock.get('name', code)
    
    try:
        # 即時分K報價
        intraday = kline_sdk.get_intraday_candles(code, "1")
        if not intraday or len(intraday) == 0:
            print(f"  {code} {name}: 無即時報價")
            continue
        
        last_bar = intraday[-1]
        last_px = float(last_bar.get('close', 0))
        total_vol = float(last_bar.get('volume', 0))
        
        if last_px == 0:
            print(f"  {code} {name}: 價格為0，跳過")
            continue
        
        # 近25日K線
        today = NOW.strftime('%Y-%m-%d')
        start = (NOW - datetime.timedelta(days=40)).strftime('%Y-%m-%d')
        
        daily = kline_sdk.get_historical_candles(code, start, today, 'D')
        if not daily or len(daily) < 25:
            print(f"  {code} {name}: K線不足（{len(daily) if daily else 0}筆）")
            continue
        
        daily_rev = list(reversed(daily))[-25:]
        closes = [float(d.get('close', 0)) for d in daily_rev]
        volumes = [float(d.get('volume', 0)) for d in daily_rev]
        n = len(closes)
        
        # MA5, MA20 for most recent complete day (index n-1)
        ma5, ma20 = ma_at(closes, n - 1)
        gap_pct = (ma20 - ma5) / ma20 * 100
        
        # 近三日量比（對比20日均量）
        avg_vol_20 = sum(volumes[-20:]) / 20
        vol_ratios = [volumes[-3+i] / avg_vol_20 for i in range(3)]
        vol_growing = all(v > 1.0 for v in vol_ratios)
        
        # 近三日價差是否收斂（取最後三個完整交易日：n-3, n-2, n-1）
        if n >= 23:
            gaps = []
            for ii in [n-3, n-2, n-1]:
                m5i, m20i = ma_at(closes, ii)
                gaps.append((m20i - m5i) / m20i * 100)
            gap_shrinking = gaps[0] < gaps[1] < gaps[2]
        else:
            gap_shrinking = False
        
        # 策略A 5條件
        cond1 = ma5 < ma20          # MA5在MA20下方
        cond2 = gap_pct < 1.0       # 價差<1%
        cond3 = gap_shrinking        # 三日收斂
        cond4 = vol_growing          # 三日量增
        cond5 = gap_pct < 2.0       # 價差<2%（緩衝）
        
        score = sum([cond1, cond2, cond3, cond4, cond5])
        
        if score >= 4:
            signal = "✅ 進場"
        elif score >= 3:
            signal = "⚠️ 觀察"
        else:
            signal = "❌ 未確認"
        
        print(f"  {code} {name}")
        print(f"    現價: {last_px:.2f} | MA5: {ma5:.2f} | MA20: {ma20:.2f} | 價差%: {gap_pct:.2f}%")
        print(f"    三日量比: {vol_ratios[0]:.2f}x / {vol_ratios[1]:.2f}x / {vol_ratios[2]:.2f}x")
        print(f"    條件(1)MA5<MA20:{cond1} (2)gap<1%:{cond2} (3)三日收斂:{cond3} (4)三日量增:{cond4} (5)gap<2%:{cond5}")
        print(f"    信號: {signal} (符合{score}/5條件)\n")
        
        results.append({
            'code': code,
            'name': name,
            'price': last_px,
            'ma5': round(ma5, 2),
            'ma20': round(ma20, 2),
            'gap_pct': round(gap_pct, 3),
            'vol_ratios': [round(v, 2) for v in vol_ratios],
            'cond1': cond1, 'cond2': cond2, 'cond3': cond3, 'cond4': cond4, 'cond5': cond5,
            'score': score,
            'signal': signal,
            'target': round(ma20, 2),
            'stop_loss': round(last_px * 0.97, 2)
        })
        
    except Exception as e:
        print(f"  {code} {name}: 錯誤 - {e}")
        import traceback; traceback.print_exc()
        continue

kline_sdk.logout()

print(f"\n=== 掃描完成，共 {len(results)} 檔 ===")
if results:
    print("\n📊 策略A信號摘要：")
    print(f"{'標的':<8} {'現價':>8} {'MA5':>8} {'MA20':>8} {'價差%':>7} {'量比':>6} {'符合':>4} {'信號':<8}")
    print("-" * 65)
    for r in sorted(results, key=lambda x: x['score'], reverse=True):
        vr = f"{r['vol_ratios'][0]:.2f}x"
        print(f"{r['code']:<8} {r['price']:>8.2f} {r['ma5']:>8.2f} {r['ma20']:>8.2f} {r['gap_pct']:>6.2f}% {vr:>6} {r['score']:>4}/5 {r['signal']:<8}")
