#!/usr/bin/env python3
"""
台股盤中即時監控 - 新策略A（MA5-MA20黃金交叉前夕）
每分鐘執行，掃描 watchlist 標的
"""

import json
import os
import sys
from datetime import datetime, timedelta

# 設定路徑
sys.path.insert(0, '/home/admin/.openclaw/workspace/fubon_api')

from fubon_client import FubonClient
from market_data import MarketData

def load_watchlist():
    """載入 watchlist"""
    watchlist_path = '/home/admin/.openclaw/workspace/stock-screener/watchlist.json'
    try:
        with open(watchlist_path) as f:
            data = json.load(f)
        return data.get('watchlist', [])
    except Exception as e:
        print(f"⚠️ 無法載入 watchlist: {e}")
        return []

def get_realtime_quote(client, stock_no):
    """取得即時報價"""
    try:
        market = MarketData(client)
        result = market.get_realtime(stock_no)
        if result and 'data' in result:
            data = result['data']
            if isinstance(data, list) and len(data) > 0:
                item = data[0]
                return {
                    'symbol': stock_no,
                    'name': item.get('name', ''),
                    'price': float(item.get('txnPrice', 0)),
                    'change': float(item.get('change', 0)),
                    'change_pct': float(item.get('changeRate', 0)),
                    'volume': int(item.get('totalVolume', 0)),
                    'bid': float(item.get('bidPrice', 0)),
                    'ask': float(item.get('askPrice', 0)),
                }
        return None
    except Exception as e:
        return None

def get_historical_klines(client, stock_no, days=25):
    """取得歷史K線資料"""
    try:
        from fubon_historical_kline import FubonHistoricalKline
        hist = FubonHistoricalKline(client)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days+10)
        
        result = hist.get_kline(
            stock_no=stock_no,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            data_type='D'  # 日K
        )
        
        if result and 'data' in result:
            return result['data']
        return []
    except Exception as e:
        return []

def analyze_strategy_a(klines, realtime_price):
    """
    分析新策略A信號
    條件：
    1. MA5 < MA20（5日均線在20日均線下方）
    2. 兩線價差（MA20-MA5）連三日縮小
    3. 20MA > 5MA 且兩線價差 < 1%
    4. 連三日量增
    停損：-3%（進場價 × 0.97）
    出場：價格反彈至 MA20 獲利了結
    """
    if len(klines) < 25:
        return None, "K線資料不足"
    
    # 取出最近25天收盤價和成交量
    closes = [float(k.get('close', 0)) for k in klines[-25:]]
    volumes = [int(k.get('volume', 0)) for k in klines[-25:]]
    
    # 計算 MA5 和 MA20
    ma5_list = []
    ma20_list = []
    for i in range(len(closes)):
        if i >= 4:
            ma5 = sum(closes[i-4:i+1]) / 5
        else:
            ma5 = sum(closes[:i+1]) / (i+1)
        if i >= 19:
            ma20 = sum(closes[i-19:i+1]) / 20
        else:
            ma20 = sum(closes[:i+1]) / (i+1)
        ma5_list.append(ma5)
        ma20_list.append(ma20)
    
    # 最新數值
    ma5 = ma5_list[-1]
    ma20 = ma20_list[-1]
    current_price = realtime_price if realtime_price else closes[-1]
    
    # 條件1: MA5 < MA20
    cond1 = ma5 < ma20
    
    # 條件2: 兩線價差連三日縮小
    gap_list = []
    for i in range(-5, 0):
        idx = i + 5
        if idx < len(ma5_list) and idx < len(ma20_list):
            gap = (ma20_list[idx] - ma5_list[idx]) / ma5_list[idx] * 100
            gap_list.append(gap)
    
    cond2 = False
    if len(gap_list) >= 3:
        # 檢查近三日 gap 是否持續縮小
        cond2 = gap_list[-1] < gap_list[-2] < gap_list[-3]
    
    # 條件3: 20MA > 5MA 且兩線價差 < 1%
    gap_current = (ma20 - ma5) / ma5 * 100
    cond3 = ma20 > ma5 and gap_current < 1.0
    
    # 條件4: 連三日量增
    avg_vol_20 = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
    vol_ratio_list = []
    for i in range(-5, 0):
        idx = i + 5
        if idx < len(volumes):
            vol_ratio = volumes[idx] / avg_vol_20 if avg_vol_20 > 0 else 0
            vol_ratio_list.append(vol_ratio)
    
    cond4 = False
    if len(vol_ratio_list) >= 3:
        cond4 = (vol_ratio_list[-1] > 1.0 and 
                 vol_ratio_list[-1] > vol_ratio_list[-2] and
                 vol_ratio_list[-2] > vol_ratio_list[-3])
    
    # 評估信號強度
    score = sum([cond1, cond2, cond3, cond4])
    
    gap_pct = (ma20 - ma5) / ma5 * 100
    
    result = {
        'ma5': round(ma5, 2),
        'ma20': round(ma20, 2),
        'gap_pct': round(gap_pct, 3),
        'cond1_ma5_lt_ma20': cond1,
        'cond2_gap_shrinking_3d': cond2,
        'cond3_gap_lt_1pct': cond3,
        'cond4_vol_increasing_3d': cond4,
        'score': score,
        'vol_ratio': round(vol_ratio_list[-1], 2) if vol_ratio_list else 0,
        'ma_dist_pct': round((current_price - ma20) / ma20 * 100, 2) if ma20 > 0 else 0,
        'entry_price': round(current_price, 2),
        'stop_loss': round(current_price * 0.97, 2),
        'target_price': round(ma20, 2),
    }
    
    if score >= 4:
        signal = "✅ 進場"
    elif score >= 3:
        signal = "⚠️ 觀察"
    else:
        signal = "❌ 不符合"
    
    return result, signal

def main():
    print(f"\n{'='*60}")
    print(f"📊 台股盤中即時監控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # 建立富邦客戶端
    try:
        client = FubonClient()
        if not client.load_config():
            print("⚠️ 無法載入富邦配置")
            return
        
        if not client.init_sdk():
            print("⚠️ 無法初始化 SDK")
            return
        
        if not client.login():
            print("⚠️ 無法登入富邦")
            return
    except Exception as e:
        print(f"⚠️ 富邦客戶端建立失敗: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 載入 watchlist
    watchlist = load_watchlist()
    if not watchlist:
        print("⚠️ watchlist 為空")
        return
    
    print(f"\n📋 掃描 {len(watchlist)} 個標的...\n")
    
    # 結果
    results = []
    strong_signals = []
    
    for item in watchlist:
        stock_no = item.get('code', '')
        name = item.get('name', '')
        if not stock_no:
            continue
        
        print(f"🔍 {stock_no} {name}...", end=" ", flush=True)
        
        # 取得即時報價
        quote = get_realtime_quote(client, stock_no)
        if not quote:
            print("⚠️ 無法取得報價")
            continue
        
        current_price = quote.get('price', 0)
        change_pct = quote.get('change_pct', 0)
        print(f"現價 {current_price} ({change_pct:+.2f}%)", end=" | ", flush=True)
        
        # 取得歷史K線
        klines = get_historical_klines(client, stock_no, days=25)
        if len(klines) < 20:
            print(f"⚠️ K線不足({len(klines)}天)")
            continue
        
        # 分析策略A
        analysis, signal = analyze_strategy_a(klines, current_price)
        if not analysis:
            print("⚠️ 分析失敗")
            continue
        
        score = analysis['score']
        gap_pct = analysis['gap_pct']
        ma_dist_pct = analysis['ma_dist_pct']
        
        print(f"MA5={analysis['ma5']} MA20={analysis['ma20']} GAP={gap_pct:.3f}% | {signal}({score}/4)")
        
        results.append({
            'code': stock_no,
            'name': name,
            'price': current_price,
            'change_pct': change_pct,
            'ma5': analysis['ma5'],
            'ma20': analysis['ma20'],
            'gap_pct': gap_pct,
            'score': score,
            'vol_ratio': analysis['vol_ratio'],
            'ma_dist_pct': ma_dist_pct,
            'signal': signal,
            'entry_price': analysis['entry_price'],
            'stop_loss': analysis['stop_loss'],
            'target_price': analysis['target_price'],
        })
        
        if score >= 3:
            strong_signals.append(results[-1])
    
    # 輸出結果
    print(f"\n{'='*60}")
    print(f"📊 掃描結果")
    print(f"{'='*60}")
    
    # 按評分排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    header = f"{'標的':<12} {'現價':>10} {'MA20距%':>10} {'MA5':>10} {'MA20':>10} {'GAP%':>8} {'vol比':>8} {'評分':>6}"
    print(f"\n{header}")
    print("-" * 90)
    
    for r in results:
        code_str = f"{r['code']} {r['name']}"
        print(f"{code_str:<14} {r['price']:>10.2f} {r['ma_dist_pct']:>+10.2f} {r['ma5']:>10.2f} {r['ma20']:>10.2f} {r['gap_pct']:>8.3f} {r['vol_ratio']:>8.2f} {r['score']:>6}/4 {r['signal']}")
    
    # 強烈信號
    if strong_signals:
        print(f"\n{'='*60}")
        print(f"🔥 符合策略A標的（3/4以上）")
        print(f"{'='*60}")
        for s in strong_signals:
            print(f"\n📌 {s['code']} {s['name']}")
            print(f"   現價: {s['price']} ({s['change_pct']:+.2f}%)")
            print(f"   MA5: {s['ma5']} | MA20: {s['ma20']} | GAP: {s['gap_pct']:.3f}%")
            print(f"   MA20距%: {s['ma_dist_pct']:+.2f}%")
            print(f"   成交量比: {s['vol_ratio']:.2f}x")
            print(f"   評分: {s['score']}/4")
            print(f"   → 進場價: {s['entry_price']}")
            print(f"   → 停損價: {s['stop_loss']} (-3%)")
            print(f"   → 目標價: {s['target_price']} (MA20)")
    
    print(f"\n{'='*60}")
    print(f"市場掃描完成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # 帳戶狀態（由 main session 填寫）
    print("📋 帳戶狀態：（留空，由 main session 填寫）")

if __name__ == '__main__':
    main()