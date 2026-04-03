#!/usr/bin/env python3
"""
台股盤中即時監控腳本
策略A：MA5-MA20黃金交叉前夕
每30分鐘執行，檢查進場訊號、停損、目標
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
    '2330': '台積電', '2317': '鴻海', '2454': '聯發科', '2382': '緯創', '2308': '台達電',
    '2303': '聯電', '3034': '聯詠', '2357': '華碩', '3008': '大立光', '2327': '國巨',
    '3481': '友達', '2353': '宏碁', '2345': '智邦', '2609': '陽明', '2610': '長榮',
    '2379': '瑞昱', '2383': '台光電', '3231': '緯穎', '3416': '龍燷', '3443': '創意',
    '3661': '世芯', '3673': 'TPK', '3711': '眾達', '3714': '富邦金', '4958': '臻鼎',
    '5009': '世界', '6108': '競國', '6116': '百祝', '6128': '上詮', '6153': '嘉澤',
    '6165': '華冠', '6176': '景碩', '6180': 'Gamania', '6182': '合正', '6191': '冀中',
    '6201': '亞翔', '6213': '聯鈞', '6221': '青新', '6230': '超豐', '6269': '台郡',
    '6271': '同欣', '6277': '精材', '6281': '全智科', '6285': '浩打', '6288': '巨路',
    '6291': '帆宣', '6505': '台塑', '6525': '環球晶', '6533': '嘉基', '6550': '新應材',
    '6560': '欣興', '6569': '晶相光', '6570': '大甲', '6575': '大立', '6579': '事欣科',
    '6581': '宣昶', '6590': '其祥', '6591': '泰金', '6592': '冠好', '6700': '明虹',
    '6706': '興中', '6715': '嘉威', '6756': '安力', '6806': '藍新科', '6881': '富邦其它',
    '6889': '大拇哥', '2008': '高興昌', '2007': '燁興', '3023': '信邦',
}

PRIORITY_STOCKS = [
    '2330','2317','2454','2382','2308','2303','3034','2357','3008','2327',
    '3481','2353','2345','2609','2610','2379','2383','3231','3416','3443',
    '3661','3673','3711','3714','4958','5009','6108','6116','6128','6153',
    '6165','6176','6180','6182','6191','6201','6213','6221','6230','6269',
    '6271','6277','6281','6285','6288','6291','6505','6525','6533','6550',
    '6560','6569','6570','6575','6579','6581','6590','6591','6592','6700',
    '6706','6715','6756','6806','6881','6889','2008','2007','3023',
]

POSITIONS_FILE = f"{SCREENER_DIR}/positions.json"
CANDIDATES_FILE = f"{OUTPUT_DIR}/latest_candidates.json"


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_positions() -> Dict[str, Dict]:
    """載入目前持倉"""
    if os.path.exists(POSITIONS_FILE):
        try:
            with open(POSITIONS_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}


def save_positions(positions: Dict):
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(positions, f, ensure_ascii=False, indent=2)


def get_realtime_quote(reststock, symbol: str) -> Optional[Dict]:
    """取得即時報價（盤中）"""
    try:
        resp = reststock.intraday.quote(symbol=symbol)
        if hasattr(resp, 'data') and resp.data:
            return resp.data[0] if isinstance(resp.data, list) else resp.data
        elif isinstance(resp, dict):
            return resp.get('data', [resp])[0] if isinstance(resp.get('data'), list) else resp
        return None
    except Exception as e:
        log(f"  ⚠️ {symbol} 報價失敗: {e}")
        return None


def get_historical_daily(client: FubonKlineSDK, symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
    """取得日K歷史數據"""
    try:
        end_date = date.today().strftime('%Y-%m-%d')
        start_date = (date.today() - timedelta(days=days * 2)).strftime('%Y-%m-%d')
        
        data = client.get_historical_candles(symbol, start_date, end_date, 'D')
        if not data or len(data) < 20:
            return None
        
        data = list(reversed(data))
        df = pd.DataFrame(data)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        df = df.tail(25).reset_index(drop=True)
        return df
    except Exception as e:
        return None


def evaluate_signal(df: pd.DataFrame) -> Optional[Dict]:
    """評估策略A進場信號"""
    if df is None or len(df) < 25:
        return None
    
    close_arr = df['close'].values
    volume_arr = df['volume'].values
    n = len(close_arr)
    
    # MA5, MA20
    ma5 = close_arr[-5:].mean()
    ma20 = close_arr[-20:].mean() if n >= 20 else close_arr.mean()
    
    # 價差%
    gap = (ma20 - ma5) / ma20 * 100 if ma20 > 0 else 0
    
    # 近4日價差（評估收斂）
    gaps = []
    for i in range(n - 4, n):
        m5_i = close_arr[max(0, i-4):i+1].mean()
        m20_i = close_arr[max(0, i-19):i+1].mean()
        gaps.append((m20_i - m5_i) / m20_i * 100 if m20_i > 0 else 0)
    
    # 近4日量
    vols = volume_arr[-4:].tolist()
    
    cond1 = ma5 < ma20                          # 5MA < 20MA
    cond2 = gaps[1] < gaps[0] and gaps[2] < gaps[1] and gaps[3] < gaps[2]  # 連三日收斂
    cond3 = gap < 1.0                            # 價差 < 1%
    cond5 = vols[3] > vols[2] > vols[1] > vols[0]  # 連三日量增
    
    cond_count = sum([cond1, cond2, cond3, cond5])
    
    entry_price = close_arr[-1]
    target = round(ma20, 2)
    stop = round(entry_price * 0.97, 2)
    
    # 信心度：0.70 起跳
    confidence = cond_count / 4.0
    
    return {
        'close': round(entry_price, 2),
        'ma5': round(ma5, 2),
        'ma20': round(ma20, 2),
        'gap_pct': round(gap, 3),
        'cond1': cond1, 'cond2': cond2, 'cond3': cond3, 'cond5': cond5,
        'cond_count': cond_count,
        'entry_price': round(entry_price, 2),
        'target_price': target,
        'stop_loss': stop,
        'target_pct': round((target - entry_price) / entry_price * 100, 2),
        'confidence': round(confidence, 2),
        'vols': [int(v) for v in vols],
        'gaps': [round(g, 3) for g in gaps],
    }


def check_positions(reststock, positions: Dict, client: FubonKlineSDK) -> tuple[List, Dict]:
    """檢查持倉，執行停損/目標"""
    stops = []
    targets = []
    updated_positions = {}
    
    for symbol, pos in positions.items():
        quote = get_realtime_quote(reststock, symbol)
        if not quote:
            updated_positions[symbol] = pos
            continue
        
        price = float(quote.get('close', 0) or quote.get('lastPrice', 0))
        if price == 0:
            updated_positions[symbol] = pos
            continue
        
        entry = float(pos['entry_price'])
        stop = float(pos['stop_loss'])
        target = float(pos['target_price'])
        name = pos.get('name', symbol)
        
        log(f"  📊 {symbol} {name}: 現价={price:.2f} 進场={entry:.2f} 停損={stop:.2f} 目標={target:.2f}")
        
        if price <= stop:
            stops.append({
                'symbol': symbol, 'name': name,
                'price': price, 'action': '停損賣出', 'reason': f'現價{price:.2f} ≤ 停損價{stop:.2f}'
            })
        elif price >= target:
            targets.append({
                'symbol': symbol, 'name': name,
                'price': price, 'action': '目標賣出', 'reason': f'現價{price:.2f} ≥ 目標價{target:.2f}'
            })
        else:
            updated_positions[symbol] = pos
    
    return stops, targets, updated_positions


def execute_sell(reststock, symbol: str, price: float, action: str) -> bool:
    """執行賣出（市價）"""
    try:
        log(f"  🔔 執行 {action} for {symbol} @ 市價...")
        # 富邦 API 市價賣出
        # account = first available account
        from fubon_neo.sdk import FubonSDK
        sdk2 = FubonSDK()
        cfg = {}
        env_path = "/home/admin/.env/fubon.env"
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    cfg[k] = v
        
        sdk2.login(cfg['ACCOUNT'], cfg['ACCT_PASSWORD'], cfg['CERT_PATH'], cfg['CERT_PASSWORD'])
        
        # 取得帳戶
        accounts = sdk2.accounting.account_balance()
        if not accounts or not accounts.data:
            log(f"  ❌ 無法取得帳戶資訊")
            return False
        
        account = accounts.data[0].account
        resp = sdk2.stock.place_order(
            account=account,
            symbol=symbol,
            buy_sell='Sell',
            price=0,  # 市價
            quantity=1,
            order_type='Market',
            price_type='Market',
        )
        
        if hasattr(resp, 'is_success') and resp.is_success:
            log(f"  ✅ {action} {symbol} 成功！")
            return True
        else:
            msg = getattr(resp, 'message', str(resp))
            log(f"  ❌ {action} {symbol} 失敗: {msg}")
            return False
    except Exception as e:
        log(f"  ❌ 賣出執行失敗: {e}")
        return False


def main():
    now = datetime.now()
    log("=" * 60)
    log(f"【盤中監控】{now.strftime('%Y-%m-%d %H:%M')} 策略A")
    log("=" * 60)
    
    # === 登入 ===
    client = FubonKlineSDK()
    if not client.login():
        log("❌ 登入失敗")
        print("❌ 登入失敗")
        return
    log("✅ 已登入富邦")
    
    reststock = client.reststock
    
    # === 檢查持倉 ===
    positions = load_positions()
    log(f"📦 目前持倉：{len(positions)} 檔")
    
    if positions:
        stops, targets, updated = check_positions(reststock, positions, client)
        
        # 執行停損
        for s in stops:
            execute_sell(reststock, s['symbol'], s['price'], '停損')
            log(f"🛑 停損：{s['symbol']} {s['name']} | 現價={s['price']:.2f} | {s['reason']}")
        
        # 執行目標
        for t in targets:
            execute_sell(reststock, t['symbol'], t['price'], '目標')
            log(f"🏠 目標：{t['symbol']} {t['name']} | 現價={t['price']:.2f} | {t['reason']}")
        
        # 更新持倉
        save_positions(updated)
        positions = updated
    else:
        log("📦 無持倉，跳過停損/目標檢查")
    
    # === 進場掃描 ===
    candidates = PRIORITY_STOCKS
    
    # 只對有候選結果的股票分析（減輕API負擔）
    if os.path.exists(CANDIDATES_FILE):
        try:
            with open(CANDIDATES_FILE) as f:
                data = json.load(f)
                cand_list = data.get('candidates', [])
                if cand_list:
                    candidates = cand_list
        except:
            pass
    
    log(f"🔍 掃描 {len(candidates)} 檔候選股票...")
    
    # 限制每次最多15檔，避免API超時
    scan_count = 0
    max_scan = 20
    signals = []
    
    for symbol in candidates:
        if scan_count >= max_scan:
            break
        
        # 取得即時報價
        quote = get_realtime_quote(reststock, symbol)
        if not quote:
            continue
        
        price = float(quote.get('close', 0) or quote.get('lastPrice', 0))
        if price == 0 or price is None:
            continue
        
        # 取得歷史日K
        df = get_historical_daily(client, symbol, days=30)
        if df is None:
            continue
        
        result = evaluate_signal(df)
        if result is None:
            continue
        
        result['symbol'] = symbol
        result['name'] = STOCK_NAMES.get(symbol, symbol)
        result['price'] = price
        
        conf = result['confidence']
        if conf >= 0.70:
            signals.append(result)
            log(f"  🎯 {symbol} {result['name']}: 信心度={conf:.2f} 現价={price:.2f} MA5={result['ma5']:.2f} MA20={result['ma20']:.2f} 差={result['gap_pct']:.3f}%")
        
        scan_count += 1
        time.sleep(0.2)
    
    # === 輸出報告 ===
    print()
    print("=" * 60)
    print(f"【盤中監控報告】{now.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # 停損/目標
    if positions.get('stops') or positions.get('targets'):
        pass  # 已在上面處理
    
    # 進場信號
    if not signals:
        print("👀 觀望：目前無符合進場條件的標的")
    else:
        signals.sort(key=lambda x: -x['confidence'])
        for s in signals:
            gap_dist = round((s['ma20'] - s['price']) / s['ma20'] * 100, 2)
            print(f"🎯進場：{s['symbol']} | 進場價={s['price']:.2f} | 停損={s['stop_loss']:.2f} | 目標={s['target_price']:.2f} | 信心度={s['confidence']:.2f}")
    
    # 持倉觀測
    if positions:
        print()
        for sym, pos in positions.items():
            quote2 = get_realtime_quote(reststock, sym)
            if quote2:
                p = float(quote2.get('close', 0) or quote2.get('lastPrice', 0))
                if p > 0:
                    entry = float(pos['entry_price'])
                    pnl = round((p - entry) / entry * 100, 2)
                    print(f"📊 {sym} {pos.get('name','')}: 現價={p:.2f} 進場={entry:.2f} 損益={pnl:+.2f}%")
    
    # 登出
    client.logout()
    
    print()
    print(f"⏰ 監控完成：{now.strftime('%H:%M:%S')}")


if __name__ == '__main__':
    main()
