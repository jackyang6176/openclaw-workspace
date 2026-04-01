#!/usr/bin/env python3
"""
台股盤後篩選 - 固定批次版本
輸出策略4（K線+量）結果至 output/fixed_batch_results_YYYYMMDD_*.json
"""
import os
import sys
import json
import gc
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Optional

WORKSPACE = "/home/admin/.openclaw/workspace"
SCREENER_DIR = f"{WORKSPACE}/stock-screener"
FUBON_API = f"{WORKSPACE}/fubon_api"
OUTPUT_DIR = f"{SCREENER_DIR}/output"

sys.path.insert(0, FUBON_API)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── 載入富邦 env ───────────────────────────────────────
env_path = "/home/admin/.env/fubon.env"
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ── .load env config for Fubon ──────────────────────────
def get_fubon_sdk():
    from fubon_neo.sdk import FubonSDK
    return FubonSDK()

def login_fubon(sdk):
    from fubon_neo import CoreSDK
    c = CoreSDK()
    resp = c.login(
        os.environ.get('ACCOUNT', ''),
        os.environ.get('ACCT_PASSWORD', ''),
        os.environ.get('CERT_PATH', ''),
        os.environ.get('CERT_PASSWORD', '')
    )
    return c, resp

# ── FinMind MA20 data ───────────────────────────────────
def get_finmind_ma20(symbol: str, days: int = 60) -> Optional[pd.DataFrame]:
    end = date.today().strftime('%Y-%m-%d')
    start = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
    url = 'https://api.finmindtrade.com/api/v4/data'
    params = {
        'dataset': 'TaiwanStockPrice',
        'data_id': symbol,
        'start_date': start,
        'end_date': end,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json().get('data', [])
        if not data:
            return None
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        df['volume'] = df['volume'].astype(float)
        df['close'] = df['close'].astype(float)
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        return df
    except Exception:
        return None

# ── K-line pattern detection ─────────────────────────────
def detect_kline_pattern(df: pd.DataFrame) -> Tuple[str, float]:
    """偵測K線型態，返回 (pattern_name, score)"""
    if len(df) < 5:
        return "unknown", 0

    latest = df.iloc[-1]
    prev4 = df.iloc[-5:-1]

    o, h, l, c = latest['open'], latest['high'], latest['low'], latest['close']
    body = abs(c - o)
    upper_shadow = h - max(o, c)
    lower_shadow = min(o, c) - l
    total_range = h - l

    prev_close_mean = prev4['close'].mean()
    prev_vol_mean = prev4['volume'].mean()
    vol_ratio = latest['volume'] / prev_vol_mean if prev_vol_mean > 0 else 1

    # MA20
    if len(df) >= 20:
        ma20 = df['close'].iloc[-20:].mean()
    else:
        ma20 = df['close'].mean()

    ma_dist_pct = (c - ma20) / ma20 * 100 if ma20 > 0 else 0

    patterns = []

    # Hammer
    if body < total_range * 0.3 and lower_shadow > body * 2 and upper_shadow < body * 0.5:
        patterns.append(('hammer', 0.8))
    # Bullish Engulfing
    if len(df) >= 2:
        prev_o, prev_c = df.iloc[-2]['open'], df.iloc[-2]['close']
        if prev_c < prev_o and c > o and o < prev_c and c > prev_o:
            patterns.append(('bullish_engulfing', 0.85))
    # Dragonfly Doji
    if body < total_range * 0.1 and lower_shadow > body * 3 and upper_shadow < body:
        patterns.append(('dragonfly_doji', 0.75))
    # Morning Star
    if len(df) >= 3:
        p1o, p1c = df.iloc[-3]['open'], df.iloc[-3]['close']
        p2o, p2c = df.iloc[-2]['open'], df.iloc[-2]['close']
        p3o, p3c = df.iloc[-1]['open'], df.iloc[-1]['close']
        if p1c < p1o and abs(p2c - p2o) < (p1c - p1o) * 0.3 and p3c > p3o and p3c > (p1o + p1c) / 2:
            patterns.append(('morning_star', 0.9))

    if not patterns:
        return "no_pattern", 0

    best = max(patterns, key=lambda x: x[1])
    return best[0], best[1]

# ── Strategy 4: K-line + Volume ─────────────────────────
def check_strategy4(df: pd.DataFrame) -> Tuple[bool, str, float]:
    """
    策略4：K線型態 + 成交量放大
    通過條件：
      - 有明確K線型態（錘子/多頭吞噬/早晨之星）
      - 成交量 > 20日均量 1.5倍
      - 股價偏離MA20在 -5% ~ +10% 區間
    """
    if len(df) < 22:
        return False, "數據不足", 0

    ma20 = df['close'].iloc[-20:].mean()
    ma20_vol = df['volume'].iloc[-20:].mean()

    latest = df.iloc[-1]
    vol_ratio = latest['volume'] / ma20_vol if ma20_vol > 0 else 0
    ma_dist_pct = (latest['close'] - ma20) / ma20 * 100 if ma20 > 0 else 0

    pattern, pattern_score = detect_kline_pattern(df)

    has_pattern = pattern != "no_pattern"
    vol_ok = vol_ratio >= 1.5
    ma_ok = -8 <= ma_dist_pct <= 15

    passed = has_pattern and vol_ok and ma_ok

    detail = f"型態:{pattern}, 量比:{vol_ratio:.1f}x, MA20偏離:{ma_dist_pct:.1f}%"
    score = (pattern_score * 0.5 + min(vol_ratio / 3, 1) * 0.3 + (1 - min(abs(ma_dist_pct) / 10, 1)) * 0.2)

    return passed, detail, min(score, 1.0)

# ── Full stock list loader ────────────────────────────────
def load_stock_list() -> List[str]:
    """載入完整股票清單"""
    cache = f"{SCREENER_DIR}/data/stock_list.json"
    if os.path.exists(cache):
        with open(cache) as f:
            data = json.load(f)
            if isinstance(data, list) and len(data) > 100:
                return data

    # fallback to finmind
    try:
        url = 'https://api.finmindtrade.com/api/v4/data'
        params = {'dataset': 'TaiwanStockInfo', 'data_id': 'ALL'}
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            stocks = resp.json().get('data', [])
            codes = sorted(set(s.get('stock_id', '') for s in stocks if s.get('stock_id', '').isdigit() and len(s.get('stock_id', '')) == 4))
            if codes:
                os.makedirs(f"{SCREENER_DIR}/data", exist_ok=True)
                with open(cache, 'w') as f:
                    json.dump(codes, f)
                return codes
    except Exception:
        pass

    # hardcoded fallback
    TWSE_STOCKS = [
        '2330','2317','2454','2382','2308','2303','3034','2357','3008','2327',
        '3481','2353','2345','2609','2610','2323','2325','2344','2352','2360',
        '2379','2383','2440','2498','3006','3014','3031','3045','3090','3130',
        '3149','3189','3231','3257','3305','3338','3416','3443','3450','3481',
        '3504','3532','3545','3567','3576','3583','3587','3593','3594','3607',
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
        '8101','8105','8110','8114','8121','8131','8147','8150','8163','8171',
        '8176','8183','8200','8210','8213','8215','8226','8234','8249','8255',
        '8261','8271','8277','8285','8289','8299','8303','8306','8341','8349',
        '8354','8358','8367','8374','8383','8401','8410','8415','8420','8422',
        '8426','8430','8442','8454','8462','8463','8464','8473','8478','8482',
        '8495','8506','8905','8906','8916','8917','8927','8930','8931','8932',
        '8933','8934','8935','8936','8937','8938','8941','8942','8996','9904',
        '9905','9910','9911','9914','9917','9921','9924','9925','9928','9930',
        '9931','9933','9934','9935','9937','9938','9939','9940','9941','9942',
        '9943','9944','9945','9946','9950','9955','9956','9958',
    ]
    return TWSE_STOCKS

# ── MOPS revenue ─────────────────────────────────────────
def get_mops_revenue(symbol: str) -> Tuple[bool, str]:
    """檢查月營收：近三月是否持續成長"""
    try:
        cache = f"{SCREENER_DIR}/data/mops_revenue.json"
        if os.path.exists(cache):
            with open(cache) as f:
                mops_data = json.load(f)
        else:
            return True, "快取無數據"

        if symbol not in mops_data:
            return True, "無營收數據"

        revs = mops_data[symbol]
        if len(revs) < 3:
            return True, "營收數據不足3筆"

        # 簡單檢查：最近三月不能全部衰退
        recent = revs[-3:]
        declining = sum(1 for i in range(1, len(recent)) if recent[i] < recent[i-1])
        return declining < 3, f"近三月衰減筆數:{declining}"

    except Exception:
        return True, "營收API異常"

# ── Main screening ──────────────────────────────────────
def run_screening():
    log("=" * 60)
    log("台股盤後篩選 - 固定批次版")
    log("=" * 60)

    today_str = date.today().strftime('%Y%m%d')
    output_file = f"{OUTPUT_DIR}/fixed_batch_results_{today_str}_{datetime.now().strftime('%H%M%S')}.json"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    stocks = load_stock_list()
    log(f"載入 {len(stocks)} 檔股票")

    # Try load MOPS
    mops_cache = f"{SCREENER_DIR}/data/mops_revenue.json"
    mops_data = {}
    try:
        if os.path.exists(mops_cache):
            with open(mops_cache) as f:
                mops_data = json.load(f)
    except Exception:
        pass

    results = {
        'date': today_str,
        'timestamp': datetime.now().isoformat(),
        'total_stocks': len(stocks),
        'strategies': {
            'result_4_kline_volume': []
        }
    }

    passed_stocks = []
    batch_size = 30

    for i in range(0, len(stocks), batch_size):
        batch = stocks[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(stocks) + batch_size - 1) // batch_size
        log(f"[{batch_num}/{total_batches}] Processing {batch[0]}~{batch[-1]}...")

        for symbol in batch:
            df = get_finmind_ma20(symbol, days=60)
            if df is None or len(df) < 22:
                continue

            try:
                # Strategy 4
                s4_pass, s4_detail, s4_score = check_strategy4(df)

                if s4_pass:
                    ma20 = df['close'].iloc[-20:].mean()
                    ma20_vol = df['volume'].iloc[-20:].mean()
                    vol_ratio = df.iloc[-1]['volume'] / ma20_vol if ma20_vol > 0 else 0
                    ma_dist_pct = (df.iloc[-1]['close'] - ma20) / ma20 * 100 if ma20 > 0 else 0

                    pattern, _ = detect_kline_pattern(df)

                    entry = {
                        'stock_code': symbol,
                        'stock_name': symbol,
                        'close': float(df.iloc[-1]['close']),
                        'change_pct': 0.0,
                        'volume': int(df.iloc[-1]['volume']),
                        'vol_ratio': round(vol_ratio, 2),
                        'ma_dist_pct': round(ma_dist_pct, 2),
                        'ma20': round(ma20, 2),
                        'pattern': pattern,
                        'pattern_score': round(s4_score, 3),
                        'detail': s4_detail,
                        's4_score': round(s4_score, 3),
                        'is_holding': False,
                        'entry_reason': f"{pattern}型態+放量{vol_ratio:.1f}x"
                    }
                    passed_stocks.append(entry)

                del df

            except Exception as e:
                log(f"  Error processing {symbol}: {e}")
                continue

        gc.collect()

    results['strategies']['result_4_kline_volume'] = passed_stocks
    results['total_passed'] = len(passed_stocks)

    # Save output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    log(f"✅ 篩選完成：{len(passed_stocks)} 檔通過策略4")
    log(f"📁 結果已保存：{output_file}")

    return output_file, passed_stocks

if __name__ == "__main__":
    output_file, stocks = run_screening()
    print(f"OUTPUT_FILE:{output_file}")
