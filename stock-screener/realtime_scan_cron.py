#!/usr/bin/env python3
"""
台股盤中即時監控腳本（每30分鐘執行）
策略A：MA5-MA20黃金交叉前夕
"""
import os
import sys
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional

WORKSPACE = "/home/admin/.openclaw/workspace"
SCREENER_DIR = f"{WORKSPACE}/stock-screener"
FUBON_API_DIR = f"{WORKSPACE}/fubon_api"
OUTPUT_DIR = f"{SCREENER_DIR}/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

sys.path.insert(0, FUBON_API_DIR)
from fubon_kline_sdk import FubonKlineSDK

STOCK_NAMES = {
    '00655L': '國泰A50正2', '2382': '緯創', '2008': '高興昌', '2007': '燁興',
    '3023': '信邦', '3008': '大立光', '2353': '宏碁', '2323': '中壽',
    '6182': '大', '3090': '日電硝', '3130': '一零', '3416': '龍燷',
    '6128': '大', '2536': '宏普', '6606': '建德', '2033': '佳大', '5388': '中磊',
    '2330': '台積電', '2317': '鴻海', '2454': '聯發科', '2308': '台達電',
    '2303': '聯電', '3034': '聯詠', '2609': '陽明', '2610': '長榮',
    '3008': '大立光', '3682': '粵海', '2440': '太空梭', '2345': '智邦',
    '3661': '世芯', '3416': '龍燷', '3504': '昇陽', '3532': '台勝科',
}

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def load_watchlist() -> List[Dict]:
    """載入 watchlist.json"""
    path = f"{SCREENER_DIR}/watchlist.json"
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('watchlist', [])
    except Exception as e:
        log(f"⚠️ 讀取 watchlist 失敗: {e}")
        return []

def get_stock_realtime(client: FubonKlineSDK, symbol: str) -> Optional[Dict]:
    """取得個股即時報價（盤中分K）"""
    try:
        data = client.get_intraday_candles(symbol, timeframe="1")
        if not data or len(data) < 1:
            return None
        # 取最後一根1分K當作即時報價
        last = data[-1]
        return {
            'symbol': symbol,
            'close': float(last.get('close', 0)),
            'volume': float(last.get('volume', 0)),
            'time': last.get('time', ''),
        }
    except Exception as e:
        log(f"  ⚠️ {symbol} 即時報價失敗: {e}")
        return None

def get_daily_klines(client: FubonKlineSDK, symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
    """取得日K資料用於計算MA"""
    try:
        end_date = date.today().strftime('%Y-%m-%d')
        start_date = (date.today() - timedelta(days=days*2)).strftime('%Y-%m-%d')
        data = client.get_historical_candles(symbol, start_date, end_date, 'D')
        if not data or len(data) < 25:
            return None
        # 富邦回傳 newest-first，翻轉
        data = list(reversed(data))
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        if len(df) > days:
            df = df.tail(days).reset_index(drop=True)
        return df
    except Exception as e:
        log(f"  ⚠️ {symbol} 日K取得失敗: {e}")
        return None

def evaluate_strategy_a(df: pd.DataFrame) -> Optional[Dict]:
    """
    評估新策略A信號
    1. 5MA < 20MA
    2. 兩線價差（MA20-MA5）連三日縮小
    3. 20MA > 5MA 且兩線價差 < 1%
    4. 今日兩線價差 < 1%
    5. 連三日量增
    """
    if df is None or len(df) < 25:
        return None

    df = df.tail(25).reset_index(drop=True)
    close_arr = df['close'].values
    volume_arr = df['volume'].values
    n = len(close_arr)

    # 計算每日MA5、MA20、價差%
    ma5_list, ma20_list, gap_list = [], [], []
    for i in range(n):
        ma5 = close_arr[max(0, i-4):i+1].mean()
        ma20 = close_arr[max(0, i-19):i+1].mean()
        ma5_list.append(ma5)
        ma20_list.append(ma20)
        gap_pct = (ma20 - ma5) / ma20 * 100 if ma20 > 0 else 0
        gap_list.append(gap_pct)

    idx_d3, idx_d2, idx_d1, idx_d0 = n-4, n-3, n-2, n-1
    if idx_d3 < 0:
        return None

    ma5_latest = ma5_list[idx_d0]
    ma20_latest = ma20_list[idx_d0]
    gap_latest = gap_list[idx_d0]
    gap_d3, gap_d2, gap_d1, gap_d0 = gap_list[idx_d3], gap_list[idx_d2], gap_list[idx_d1], gap_list[idx_d0]
    vol_d3, vol_d2, vol_d1, vol_d0 = volume_arr[idx_d3], volume_arr[idx_d2], volume_arr[idx_d1], volume_arr[idx_d0]

    cond1 = ma5_latest < ma20_latest
    cond2 = (gap_d2 < gap_d3) and (gap_d1 < gap_d2) and (gap_d0 < gap_d1)
    cond3 = cond1 and (gap_latest < 1.0)
    cond4 = gap_latest < 1.0
    cond5 = (vol_d0 > vol_d1) and (vol_d1 > vol_d2) and (vol_d2 > vol_d3)

    cnt = sum([cond1, cond2, cond3, cond4, cond5])

    return {
        'ma5': round(ma5_latest, 2),
        'ma20': round(ma20_latest, 2),
        'gap_pct': round(gap_latest, 3),
        'cond1': cond1,
        'cond2': cond2,
        'cond3': cond3,
        'cond4': cond4,
        'cond5': cond5,
        'cond_count': cnt,
        'vol_today': int(vol_d0),
        'vol_ratio': round(vol_d0 / vol_d3, 2) if vol_d3 > 0 else 0,
        'ma_dist_pct': round((ma20_latest - close_arr[idx_d0]) / ma20_latest * 100, 2),
    }

def main():
    log("=" * 70)
    log(f"【盤中監控】新策略A掃描 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log("=" * 70)

    # 登入富邦
    client = FubonKlineSDK()
    if not client.login():
        log("❌ 富邦登入失敗")
        return
    log("✅ 富邦登入成功")

    # 載入 watchlist
    watchlist = load_watchlist()
    if not watchlist:
        log("⚠️ watchlist 為空")
        client.logout()
        return

    # 過濾有策略A tag 的標的
    candidates = [s for s in watchlist if s.get('strategy', '').startswith('策略A') or 'strategy_a' in s.get('pattern', '').lower()]
    if not candidates:
        candidates = watchlist  # 如果沒有策略A tag，全量掃描

    log(f"📋 共 {len(candidates)} 檔候選")

    results = []
    now_hour = datetime.now().hour

    for i, item in enumerate(candidates):
        sym = item['code']
        name = item.get('name', STOCK_NAMES.get(sym, sym))
        log(f"[{i+1}/{len(candidates)}] {sym} {name}...")

        # 即時報價
        rt = get_stock_realtime(client, sym)
        if rt is None:
            log(f"  ⚠️ 無法取得即時報價")
            continue

        current_price = rt['close']
        ma20 = item.get('ma20', 0)
        ma_dist_pct = item.get('ma_dist_pct', 0)

        # 計算 MA20距%
        if ma20 > 0:
            ma20_dist = round((current_price - ma20) / ma20 * 100, 2)
        else:
            ma20_dist = None

        # 評估信號強度
        sig_strength = item.get('ma_dist_pct', 0)

        # 評估是否即將進場
        # 條件：MA5 < MA20 且價差 < 1% 且 MA20距% 接近0
        ma5 = item.get('ma5', 0)
        gap_pct = item.get('gap_pct', 0)

        entry_signal = "⚡關注" if (ma5 < ma20 if ma20 > 0 else False) and gap_pct < 1.0 and abs(ma20_dist or 999) < 2 else "—"

        results.append({
            'code': sym,
            'name': name,
            'price': current_price,
            'ma20': ma20,
            'ma20_dist': ma20_dist,
            'gap_pct': gap_pct,
            'entry_signal': entry_signal,
        })

        time.sleep(0.3)

    client.logout()

    # === 產出報告 ===
    print()
    print("=" * 80)
    print(f"【盤中監控 {datetime.now().strftime('%H:%M')}】新策略A — 掃描 {len(candidates)} 檔")
    print("=" * 80)
    print()

    if not results:
        print("📊 暫無有效資料")
        print()
        print("帳戶狀態：")
        print("  （由 main session 填寫）")
        return

    print(f"{'代碼':<6} {'名稱':<8} {'現價':>8} {'MA20距%':>8} {'價差%':>6} {'信號':<6}")
    print("-" * 50)
    for r in sorted(results, key=lambda x: x['ma20_dist'] or 999):
        ma20_d = f"{r['ma20_dist']:+.2f}%" if r['ma20_dist'] is not None else "N/A"
        print(f"{r['code']:<6} {r['name']:<8} {r['price']:>8.2f} {ma20_d:>8} {r['gap_pct']:>6.3f}% {r['entry_signal']:<6}")

    print()
    print("帳戶狀態：")
    print("  （由 main session 填寫）")
    print()
    print("=" * 80)

    return results

if __name__ == '__main__':
    main()
