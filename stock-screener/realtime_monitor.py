#!/usr/bin/env python3
"""
台股盤中即時監控腳本（每30分鐘執行一次）
策略A：MA5-MA20黃金交叉前夕
"""
import os
import sys
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional

WORKSPACE = "/home/admin/.openclaw/workspace"
SCREENER_DIR = f"{WORKSPACE}/stock-screener"
FUBON_API_DIR = f"{WORKSPACE}/fubon_api"
sys.path.insert(0, FUBON_API_DIR)
from fubon_kline_sdk import FubonKlineSDK

STOCK_NAMES = {
    '00655L': '國泰A50正2', '2008': '高興昌', '2007': '燁興',
    '3023': '信邦', '3008': '大立光',
}

def get_stock_data_fubon(client: FubonKlineSDK, symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
    """使用富邦API獲取股票日K數據"""
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = '2026-02-01'
        data = client.get_historical_candles(symbol, start_date, end_date, 'D')
        if not data or len(data) < 20:
            return None
        data = list(reversed(data))
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        for col in ['close', 'volume', 'open', 'high', 'low']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['close', 'volume']).reset_index(drop=True)
        if len(df) > days:
            df = df.tail(days).reset_index(drop=True)
        return df
    except Exception as e:
        print(f"  ⚠️ {symbol} 資料取得失敗: {e}")
        return None

def get_realtime_quote(client, symbol: str) -> Optional[Dict]:
    """取得即時報價"""
    try:
        resp = client.reststock.intraday.quote(symbol=symbol)
        if isinstance(resp, dict):
            d = resp
        else:
            d = {}
        
        price = float(d.get('lastPrice', d.get('closePrice', 0)))
        volume = int(d.get('total', {}).get('tradeVolume', 0) if isinstance(d.get('total'), dict) else 0)
        change = float(d.get('change', 0))
        change_pct = float(d.get('changePercent', 0))
        high = float(d.get('highPrice', 0))
        low = float(d.get('lowPrice', 0))
        open_p = float(d.get('openPrice', 0))
        reference = float(d.get('referencePrice', 0))
        
        return {
            'price': price, 'volume': volume, 'change': change,
            'change_pct': change_pct, 'high': high, 'low': low,
            'open': open_p, 'reference': reference, 'raw': d
        }
    except Exception as e:
        print(f"  ⚠️ {symbol} 即時報價失敗: {e}")
        return None

def analyze_strategy_a_realtime(df: pd.DataFrame) -> Optional[Dict]:
    """分析是否為MA5-MA20黃金交叉前夕"""
    if df is None or len(df) < 25:
        return None
    
    df_local = df.tail(25).reset_index(drop=True)
    close_arr = df_local['close'].values.astype(float)
    volume_arr = df_local['volume'].values.astype(float)
    dates_arr = df_local['date'].dt.strftime('%Y-%m-%d').values
    
    n = len(close_arr)
    
    ma5_list, ma20_list, gap_list = [], [], []
    for i in range(n):
        ma5 = float(close_arr[max(0, i-4):i+1].mean())
        ma20 = float(close_arr[max(0, i-19):i+1].mean())
        ma5_list.append(ma5)
        ma20_list.append(ma20)
        gap_pct = float((ma20 - ma5) / ma20 * 100) if ma20 > 0 else 0.0
        gap_list.append(gap_pct)
    
    idx_d3 = n - 4
    idx_d2 = n - 3
    idx_d1 = n - 2
    idx_d0 = n - 1
    
    if idx_d3 < 0:
        return None
    
    ma5_latest = ma5_list[idx_d0]
    ma20_latest = ma20_list[idx_d0]
    gap_latest = gap_list[idx_d0]
    
    gap_d3 = gap_list[idx_d3]
    gap_d2 = gap_list[idx_d2]
    gap_d1 = gap_list[idx_d1]
    gap_d0 = gap_list[idx_d0]
    
    vol_d3 = float(volume_arr[idx_d3])
    vol_d2 = float(volume_arr[idx_d2])
    vol_d1 = float(volume_arr[idx_d1])
    vol_d0 = float(volume_arr[idx_d0])
    
    cond1 = bool(ma5_latest < ma20_latest)
    cond2 = bool((gap_d2 < gap_d3) and (gap_d1 < gap_d2) and (gap_d0 < gap_d1))
    cond3 = bool(cond1 and (gap_latest < 1.0))
    cond4 = bool(gap_latest < 1.0)
    cond5 = bool((vol_d0 > vol_d1) and (vol_d1 > vol_d2) and (vol_d2 > vol_d3))
    
    cond_count = sum([cond1, cond2, cond3, cond4, cond5])
    
    # 信心度（修正：負價差代表已穿越，應處罰）
    base_conf = cond_count / 5.0 * 0.7
    # gap_penalty：gap越接近0且為正（5MA在20MA下方逼近）越好，負值（已穿越）則處罰
    if gap_latest >= 0:
        gap_penalty = max(0.0, (1.0 - gap_latest) / 1.0) * 0.2
    else:
        gap_penalty = gap_latest * 0.2  # 負值直接削弱信心
    vol_conf = 0.1 if cond5 else 0.0
    confidence = min(1.0, max(0.0, base_conf + gap_penalty + vol_conf))
    
    entry_price = float(close_arr[idx_d0])
    
    return {
        'date': str(dates_arr[idx_d0]),
        'close': round(entry_price, 2),
        'ma5': round(ma5_latest, 2),
        'ma20': round(ma20_latest, 2),
        'gap_pct': round(gap_latest, 3),
        'gap_d3': round(gap_d3, 3),
        'gap_d2': round(gap_d2, 3),
        'gap_d1': round(gap_d1, 3),
        'gap_d0': round(gap_d0, 3),
        'cond1': cond1, 'cond2': cond2, 'cond3': cond3, 'cond4': cond4, 'cond5': cond5,
        'cond_count': int(cond_count),
        'confidence': round(float(confidence), 3),
        'entry_price': round(entry_price, 2),
        'target_price': round(ma20_latest, 2),
        'stop_loss': round(entry_price * 0.97, 2),
        'vol_today': int(vol_d0), 'vol_yesterday': int(vol_d1),
        'vol_2day': int(vol_d2), 'vol_3day': int(vol_d3),
    }

def main():
    now = datetime.now()
    ts = now.strftime('%H:%M')
    print(f"\n{'='*60}")
    print(f"⏰ 盤中監控 {ts}（策略A：MA5-MA20黃金交叉前夕）")
    print(f"{'='*60}")
    
    client = FubonKlineSDK()
    if not client.login():
        print("❌ 富邦登入失敗")
        return
    print("✅ 已登入富邦")
    
    wl_path = f"{SCREENER_DIR}/watchlist.json"
    with open(wl_path) as f:
        wl_data = json.load(f)
    
    watchlist = wl_data.get('watchlist', [])
    holdings = wl_data.get('holdings', {})
    symbols = [w['code'] for w in watchlist]
    
    print(f"📋 監控標的：{', '.join(symbols)}")
    print(f"💼 持有部位：{json.dumps(holdings, ensure_ascii=False)}")
    
    # 即時報價
    quotes = {}
    for sym in symbols:
        q = get_realtime_quote(client, sym)
        if q:
            quotes[sym] = q
        time.sleep(0.5)
    
    # 評估進場信號
    entries, observations = [], []
    
    for w in watchlist:
        sym = w['code']
        name = w.get('name', sym)
        
        df = get_stock_data_fubon(client, sym, days=30)
        time.sleep(0.5)
        
        current_price = 0.0
        if sym in quotes and quotes[sym]['price'] > 0:
            current_price = quotes[sym]['price']
        
        if df is None:
            observations.append({
                'symbol': sym, 'name': name,
                'price': current_price,
                'ma20_dist_pct': None,
                'confidence': 0.0,
                'cond_count': 0,
                'gap_pct': None,
                'reason': '日K資料不足'
            })
            continue
        
        result = analyze_strategy_a_realtime(df)
        
        if current_price <= 0:
            current_price = result['close']
        
        ma20 = result['ma20']
        ma20_dist = float((current_price - ma20) / ma20 * 100) if ma20 > 0 else 0.0
        
        result['symbol'] = sym
        result['name'] = name
        result['current_price'] = round(float(current_price), 2)
        result['ma20_dist_pct'] = round(ma20_dist, 3)
        
        if result['confidence'] >= 0.70:
            entries.append(result)
        
        observations.append({
            'symbol': sym, 'name': name,
            'price': round(float(current_price), 2),
            'ma20_dist_pct': round(ma20_dist, 3),
            'confidence': result['confidence'],
            'cond_count': result['cond_count'],
            'gap_pct': result['gap_pct'],
        })
    
    # 檢查持有部位
    sell_actions = []
    for sym, hold in holdings.items():
        entry_price = float(hold.get('entry_price', 0))
        if entry_price <= 0:
            continue
        
        q = quotes.get(sym)
        current_price = 0.0
        if q:
            current_price = float(q['price'])
        
        if current_price <= 0:
            q = get_realtime_quote(client, sym)
            if q:
                current_price = float(q['price'])
            time.sleep(0.5)
        
        if current_price <= 0:
            continue
        
        stop_loss = round(entry_price * 0.97, 2)
        
        df = get_stock_data_fubon(client, sym, days=30)
        ma20 = None
        if df is not None and len(df) >= 20:
            ma20 = round(float(df['close'].tail(20).mean()), 2)
        time.sleep(0.5)
        
        if current_price <= stop_loss:
            sell_actions.append({
                'symbol': sym, 'name': hold.get('name', sym),
                'price': round(float(current_price), 2),
                'action': '停損',
                'entry': entry_price,
                'stop_loss': stop_loss,
                'pnl_pct': round(float((current_price - entry_price) / entry_price * 100), 2)
            })
        elif ma20 and current_price >= float(ma20):
            sell_actions.append({
                'symbol': sym, 'name': hold.get('name', sym),
                'price': round(float(current_price), 2),
                'action': '目標',
                'entry': entry_price,
                'ma20': ma20,
                'pnl_pct': round(float((current_price - entry_price) / entry_price * 100), 2)
            })
    
    try:
        client.logout()
    except Exception:
        pass
    
    # === 產出報告 ===
    print(f"\n{'='*60}")
    print("📊 持有部位檢查")
    print(f"{'='*60}")
    if sell_actions:
        for s in sell_actions:
            emoji = '🛑' if s['action'] == '停損' else '🏠'
            print(f"  {emoji} {s['symbol']} {s['name']} | 現價:{s['price']} | {s['action']} | 報酬:{s['pnl_pct']:+.2f}%")
    else:
        print("  ✅ 無觸發停損/目標")
    
    print(f"\n{'='*60}")
    print("🎯 進場信號（信心度 ≥ 0.70）")
    print(f"{'='*60}")
    if entries:
        for e in sorted(entries, key=lambda x: -x['confidence']):
            print(f"  📈 {e['symbol']} {e['name']} | 進:{e['entry_price']} | 停損:{e['stop_loss']} | 目標:{e['target_price']} | 信心:{e['confidence']:.2f} | MA20距:{e['ma20_dist_pct']:+.2f}%")
    else:
        print("  🔸 無符合進場條件標的")
    
    print(f"\n{'='*60}")
    print("👀 觀望清單")
    print(f"{'='*60}")
    for o in sorted(observations, key=lambda x: -(x.get('confidence', 0) or 0)):
        conf_str = f"{o.get('confidence', 0):.2f}" if o.get('confidence') else '-'
        cond_str = f"{o.get('cond_count', 0)}/5" if 'cond_count' in o else '-'
        ma20_dist = o.get('ma20_dist_pct', 0)
        dist_str = f"{ma20_dist:+.2f}%" if ma20_dist is not None else '-'
        print(f"  👁 {o['symbol']} {o['name']} | 現價:{o['price']} | MA20距:{dist_str} | 信心:{conf_str} | 條件:{cond_str}")
    
    # 保存狀態
    state = {
        'timestamp': now.isoformat(),
        'quotes': {k: {kk: vv for kk, vv in v.items() if kk != 'raw'} for k, v in quotes.items()},
        'entries': entries,
        'observations': observations,
        'sell_actions': sell_actions,
    }
    state_file = f"{SCREENER_DIR}/output/realtime_state_{now.strftime('%Y%m%d_%H%M')}.json"
    os.makedirs(f"{SCREENER_DIR}/output", exist_ok=True)
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    
    print(f"\n⏰ 監控完成 {now.strftime('%H:%M:%S')}")
    print(f"💾 狀態已保存")

if __name__ == '__main__':
    main()
