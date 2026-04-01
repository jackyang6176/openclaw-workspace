#!/usr/bin/env python3
"""
策略A新篩選器 - 使用yfinance數據
針對 result_4_kline_volume 候選股，進一步計算：
- 10日高低差距%（橫盤判斷：需 < 8%）
- 連三日量增（今日 > 昨日 > 前日 > 大前日）
- 型態（錘子/多頭吞噬）
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
OUTPUT_DIR = f"{SCREENER_DIR}/output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Stock list ────────────────────────────────────────────
TWSE_STOCKS = [
    '2330','2317','2454','2382','2308','2303','3034','2357','3008','2327',
    '3481','2353','2345','2609','2610','2323','2325','2344','2352','2360',
    '2379','2383','2440','2498','3006','3014','3031','3045','3090','3130',
    '3149','3189','3231','3257','3305','3338','3416','3443','3450','3481',
    '3504','3532','3545','3567','3576','3532','3583','3587','3593','3594','3607',
    '3617','3652','3661','3665','3673','3682','3698','3702','3706','3711',
    '3714','3740','3800','3838','4001','4002','4107','4137','4401','4414',
    '4426','4523','4549','4551','4562','4580','4604','4702','4707','4720',
    '4807','4904','4930','4938','4952','4958','4960','5009','5104','5120',
    '5130','5151','5203','5225','5234','5264','5309','5387','5434','5469',
    '5474','5487','5511','5512','5522','5530','5536','5607','5609','5701',
    '5702','5820','5876','5880','5903','5904','5906','6005','6024','6026',
    '6108','6112','6115','6116','6120','6128','6136','6147','6152','6153',
    '6155','6164','6165','6172','6174','6176','6180','6182','6184','6185',
    '6190','6191','6192','6201','6202','6205','6206','6208','6213','6214',
    '6216','6220','6221','6223','6225','6226','6229','6230','6234','6235',
    '6239','6244','6257','6269','6270','6271','6274','6275','6279','6281',
    '6283','6285','6288','6289','6290','6291','6292','6293','6294','6505',
    '6525','6531','6533','6535','6541','6542','6550','6560','6569','6570',
    '6575','6579','6581','6585','6590','6591','6592','6594','6603','6625',
    '6655','6700','6706','6715','6721','6752','6756','6806','6881','6889',
    '8011','8016','8021','8033','8039','8046','8050','8069','8070','8081',
    '8101','8105','8110','8114','8121','8147','8150','8163','8171','8176',
    '8183','8200','8210','8213','8215','8226','8234','8249','8255','8261',
    '8271','8277','8285','8289','8299','8303','8306','8341','8349','8354',
    '8358','8367','8374','8383','8401','8410','8415','8420','8422','8426',
    '8430','8442','8454','8462','8463','8464','8473','8478','8482','8495',
    '8506','8905','8906','8916','8917','8927','8930','8931','8932','8933',
    '8934','8935','8936','8937','8938','8941','8942','8996','9904','9905',
    '9910','9911','9914','9917','9921','9924','9925','9928','9930','9931',
    '9933','9934','9935','9937','9938','9939','9940','9941','9942','9943',
    '9944','9945','9946','9950','9955','9956','9958',
]

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ── K-line pattern detection ──────────────────────────────
def detect_kline_pattern(df: pd.DataFrame) -> Tuple[str, float, str]:
    """
    偵測K線型態，返回 (pattern_name, score, description)
    """
    if len(df) < 5:
        return "unknown", 0, "數據不足"

    latest = df.iloc[-1]
    prev1 = df.iloc[-2] if len(df) >= 2 else None
    prev2 = df.iloc[-3] if len(df) >= 3 else None
    prev3 = df.iloc[-4] if len(df) >= 4 else None
    prev4 = df.iloc[-5] if len(df) >= 5 else None

    o, h, l, c = latest['open'], latest['high'], latest['low'], latest['close']
    body = abs(c - o)
    upper_shadow = h - max(o, c)
    lower_shadow = min(o, c) - l
    total_range = h - l if h > l else 1

    prev_close_mean = df.iloc[-5:-1]['close'].mean() if len(df) >= 5 else df['close'].mean()
    prev_vol_mean = df.iloc[-5:-1]['volume'].mean() if len(df) >= 5 else df['volume'].mean()
    vol_ratio = latest['volume'] / prev_vol_mean if prev_vol_mean > 0 else 1

    # MA20
    if len(df) >= 20:
        ma20 = df['close'].iloc[-20:].mean()
    else:
        ma20 = df['close'].mean()

    ma_dist_pct = (c - ma20) / ma20 * 100 if ma20 > 0 else 0

    patterns = []

    # Hammer (錘子)
    if body < total_range * 0.3 and lower_shadow > body * 2 and upper_shadow < body * 0.5:
        patterns.append(('hammer', 0.8, '錘子線（下影線較長，空方反轉）'))
    
    # Bullish Engulfing (多頭吞噬)
    if prev1 is not None:
        prev_o, prev_c = prev1['open'], prev1['close']
        if prev_c < prev_o and c > o and o <= prev_c and c >= prev_o:
            patterns.append(('bullish_engulfing', 0.85, '多頭吞噬（两K線組合多方反轉）'))

    # Dragonfly Doji (蜻蜓十字)
    if body < total_range * 0.1 and lower_shadow > body * 3 and upper_shadow < body:
        patterns.append(('dragonfly_doji', 0.75, '蜻蜓十字（下方十字，反轉訊號）'))

    # Morning Star (早晨之星)
    if prev1 is not None and prev2 is not None:
        p1o, p1c = prev2['open'], prev2['close']
        p2o, p2c = prev1['open'], prev1['close']
        p3o, p3c = latest['open'], latest['close']
        if p1c < p1o and abs(p2c - p2o) < (p1c - p1o) * 0.3 and p3c > p3o and p3c > (p1o + p1c) / 2:
            patterns.append(('morning_star', 0.9, '早晨之星（三K線組合多方反轉）'))

    if not patterns:
        return "no_pattern", 0, "無明確型態"

    best = max(patterns, key=lambda x: x[1])
    return best[0], best[1], best[2]

# ── Get yfinance data ─────────────────────────────────────
def get_yahoo_data(symbol: str, days: int = 60) -> Optional[pd.DataFrame]:
    """使用yfinance獲取台股數據"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{symbol}.TW")
        end = date.today()
        start = end - timedelta(days=days * 2)
        df = ticker.history(start=start, end=end)
        if df is None or df.empty:
            return None
        df = df.reset_index()
        df.columns = [col.lower() for col in df.columns]
        df = df.rename(columns={'date': 'date', 'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'})
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
        df = df.dropna(subset=['close', 'volume'])
        return df.tail(days)
    except Exception as e:
        return None

# ── Strategy 4 check ─────────────────────────────────────
def check_strategy4(df: pd.DataFrame) -> Tuple[bool, str, float, dict]:
    """
    策略4：K線型態 + 成交量放大
    """
    if len(df) < 22:
        return False, "數據不足", 0, {}

    ma20 = df['close'].iloc[-20:].mean()
    ma20_vol = df['volume'].iloc[-20:].mean()

    latest = df.iloc[-1]
    vol_ratio = latest['volume'] / ma20_vol if ma20_vol > 0 else 0
    ma_dist_pct = (latest['close'] - ma20) / ma20 * 100 if ma20 > 0 else 0

    pattern, pattern_score, pattern_desc = detect_kline_pattern(df)

    has_pattern = pattern != "no_pattern"
    vol_ok = vol_ratio >= 1.5
    ma_ok = -8 <= ma_dist_pct <= 15

    passed = has_pattern and vol_ok and ma_ok

    detail = f"型態:{pattern}, 量比:{vol_ratio:.1f}x, MA20偏離:{ma_dist_pct:.1f}%"
    score = (pattern_score * 0.5 + min(vol_ratio / 3, 1) * 0.3 + (1 - min(abs(ma_dist_pct) / 10, 1)) * 0.2)

    info = {
        'pattern': pattern,
        'pattern_desc': pattern_desc,
        'pattern_score': pattern_score,
        'vol_ratio': round(vol_ratio, 2),
        'ma20': round(ma20, 2),
        'ma_dist_pct': round(ma_dist_pct, 2),
        'score': round(min(score, 1.0), 2),
        'close': round(float(latest['close']), 2),
        'open': round(float(latest['open']), 2),
        'high': round(float(latest['high']), 2),
        'low': round(float(latest['low']), 2),
        'volume': int(latest['volume']),
    }

    return passed, detail, min(score, 1.0), info

# ── New Strategy A additional checks ─────────────────────
def check_strategy_a_additional(df: pd.DataFrame) -> dict:
    """
    新策略A額外條件：
    - 10日高低差距%（橫盤判斷：需 < 8%）
    - 連三日量增（今日 > 昨日 > 前日 > 大前日）
    """
    if len(df) < 10:
        return {'range_pct': None, 'vol3_up': False, 'vol3_detail': '數據不足'}

    # 10日高低差距%
    last10 = df.tail(10)
    high10 = last10['high'].max()
    low10 = last10['low'].min()
    close_last = df.iloc[-1]['close']
    range_pct = (high10 - low10) / close_last * 100 if close_last > 0 else 100

    # 連三日量增
    if len(df) >= 4:
        v4 = df.iloc[-4]['volume']  # 大前日
        v3 = df.iloc[-3]['volume']  # 前日
        v2 = df.iloc[-2]['volume']  # 昨日
        v1 = df.iloc[-1]['volume']  # 今日
        vol3_up = (v1 > v2 > v3 > v4)
        vol3_detail = f"今日:{v1:,} > 昨日:{v2:,} > 前日:{v3:,} > 大前日:{v4:,}"
    else:
        vol3_up = False
        vol3_detail = "數據不足"

    return {
        'range_pct': round(range_pct, 2),
        'vol3_up': vol3_up,
        'vol3_detail': vol3_detail,
        'high10': round(high10, 2),
        'low10': round(low10, 2),
    }

# ── Main screener ─────────────────────────────────────────
def run_screener():
    log("=" * 60)
    log("策略A新篩選器 - yfinance版本")
    log(f"日期：{date.today().strftime('%Y-%m-%d')}")
    log("=" * 60)

    results = {
        'date': date.today().strftime('%Y%m%d'),
        'timestamp': datetime.now().isoformat(),
        'total_stocks': len(TWSE_STOCKS),
        'strategy4_candidates': [],
        'strategy_a_final': [],
    }

    passed_s4 = []
    
    # Batch processing
    batch_size = 50
    total_batches = (len(TWSE_STOCKS) + batch_size - 1) // batch_size
    
    for batch_idx in range(total_batches):
        batch = TWSE_STOCKS[batch_idx * batch_size : (batch_idx + 1) * batch_size]
        log(f"[{batch_idx+1}/{total_batches}] Processing batch {batch_idx+1}...")
        
        for symbol in batch:
            df = get_yahoo_data(symbol, days=60)
            if df is None or len(df) < 25:
                continue
            
            passed, detail, score, info = check_strategy4(df)
            if passed:
                s4_entry = {
                    'symbol': symbol,
                    'detail': detail,
                    'score': score,
                    **info,
                }
                passed_s4.append(s4_entry)
                log(f"  ✅ {symbol}: {detail} (score={score:.2f})")
            
            time.sleep(0.1)  # be nice to yfinance
        
        # Save intermediate
        results['strategy4_candidates'] = passed_s4
        if batch_idx < total_batches - 1:
            time.sleep(2)  # pause between batches

    log(f"\n策略4初篩通過：{len(passed_s4)} 檔")

    # ── Apply Strategy A additional filters ──────────────────
    log("\n套用策略A額外條件（10日橫盤<8% + 三日量增）...")
    
    strategy_a_final = []
    for entry in passed_s4:
        symbol = entry['symbol']
        df = get_yahoo_data(symbol, days=30)
        if df is None:
            continue
        
        a_info = check_strategy_a_additional(df)
        
        entry['range_pct'] = a_info['range_pct']
        entry['vol3_up'] = a_info['vol3_up']
        entry['vol3_detail'] = a_info['vol3_detail']
        
        # Apply Strategy A: range < 8% AND vol3_up
        if a_info['range_pct'] is not None and a_info['vol3_up']:
            if a_info['range_pct'] < 8:
                strategy_a_final.append(entry)
                log(f"  🎯 {symbol}: 橫盤{a_info['range_pct']:.1f}% + 三日量增 ✅")
        
        time.sleep(0.1)

    results['strategy_a_final'] = strategy_a_final

    # Save output
    output_file = f"{OUTPUT_DIR}/strategy_a_results_{date.today().strftime('%Y%m%d')}_{datetime.now().strftime('%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    log(f"\n✅ 篩選完成")
    log(f"策略4候選：{len(passed_s4)} 檔")
    log(f"策略A最終：{len(strategy_a_final)} 檔")
    log(f"📁 結果已保存：{output_file}")
    
    return results

if __name__ == '__main__':
    results = run_screener()
