#!/usr/bin/env python3
"""台股 MA5-MA20 黃金交叉前夕策略 - 盤中監控 v2"""
import os, sys, math
from datetime import datetime, timedelta, timezone

# ── 路徑設定 ──────────────────────────────────────────────
sys.path.insert(0, '/home/admin/.local/lib/python3.12/site-packages')

from dotenv import load_dotenv
load_dotenv('/home/admin/.env/fubon.env')

from fubon_neo.sdk import FubonSDK

# ── env ────────────────────────────────────────────────────
api_key     = os.getenv('FUBON_API_KEY')
cert_path   = os.getenv('CERT_PATH')
cert_pwd    = os.getenv('CERT_PASSWORD')
account     = os.getenv('ACCOUNT')
acct_pwd    = os.getenv('ACCT_PASSWORD')

# ── 觀察名單 ────────────────────────────────────────────────
DEFAULT_WATCHLIST = [
    '2330', '2454', '2317', '2303', '1301',
    '2881', '2891', '2882', '2892', '2002',
    '1216', '1101', '1102', '1303', '1326',
    '1722', '2108', '2207', '2408', '3661',
]
WL_PATH = '/home/admin/.openclaw/workspace/watchlist_stocks.txt'
watchlist = []
if os.path.exists(WL_PATH):
    with open(WL_PATH) as f:
        for line in f:
            code = line.strip()
            if code and not code.startswith('#'):
                watchlist.append(code)
if not watchlist:
    watchlist = DEFAULT_WATCHLIST

now_str = datetime.now().strftime('%H:%M:%S')
print(f"[{now_str}] 開始掃描 {len(watchlist)} 檔股票...")

# ── 登入 ────────────────────────────────────────────────────
sdk = FubonSDK()
res = sdk.login(account, acct_pwd, cert_path, cert_pwd)
if not res.is_success:
    print(f"❌ 登入失敗: {res.message}")
    sys.exit(1)
account_info = res.data[0]
print(f"✅ 登入成功: {account_info.name} ({account_info.account})")

# ── 取持倉 ─────────────────────────────────────────────────
def get_positions():
    try:
        res = sdk.account.balance()
        if not res.is_success:
            return []
        data = res.data
        positions = []
        if isinstance(data, list):
            for item in data:
                sym = getattr(item, 'symbol', None)
                qty = getattr(item, 'quantity', None)
                if sym and qty:
                    try:
                        q = int(qty)
                    except:
                        q = 0
                    if q > 0:
                        positions.append({
                            'symbol':   sym,
                            'quantity': q,
                            'avg_cost': float(getattr(item, 'avg_cost', 0) or 0),
                        })
        return positions
    except Exception as e:
        print(f"   ⚠️ 取持倉失敗: {e}")
    return []

positions = get_positions()
print(f"   現有部位: {len(positions)} 檔")

# ── 取報價 ─────────────────────────────────────────────────
def get_quote(symbol):
    try:
        res = sdk.marketdata.rest_client.stock.intraday.quote(symbol=symbol)
        if not res.is_success:
            return None
        d = res.data
        if isinstance(d, list):
            d = d[0] if d else {}
        close = d.get('close', d.get('lastPrice', 0))
        return {
            'symbol':    symbol,
            'close':     float(close) if close else 0,
            'open':      float(d.get('open', 0) or 0),
            'high':      float(d.get('high', 0) or 0),
            'low':       float(d.get('low', 0) or 0),
            'volume':    int(d.get('tradeVolume', d.get('volume', 0) or 0)),
        }
    except Exception as e:
        return None

# ── 取日K（candles）─────────────────────────────
def get_daily_candles(symbol, days=25):
    try:
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days * 2)
        res = sdk.marketdata.rest_client.stock.candles(
            symbol=symbol,
            start=f'{start_date.year}-{start_date.month:02d}-{start_date.day:02d}',
            end=f'{end_date.year}-{end_date.month:02d}-{end_date.day:02d}',
            duration='daily'
        )
        if not res.is_success:
            return None
        raw = res.data
        if not isinstance(raw, list):
            raw = [raw]
        # 只取 close 欄位
        closes = []
        for c in raw:
            cl = c.get('close')
            if cl is not None:
                try:
                    closes.append(float(cl))
                except:
                    pass
        # 取最近20個交易日
        return closes[-20:] if len(closes) >= 20 else None
    except Exception as e:
        return None

# ── 均線計算 ───────────────────────────────────────────────
def calc_ma(vals, n):
    if not vals or len(vals) < n:
        return None
    return sum(vals[-n:]) / n

# ── 評估信號 ───────────────────────────────────────────────
def evaluate_signal(symbol, quote, candles):
    """
    策略A：MA5-MA20 黃金交叉前夕
    1. MA5 < MA20
    2. 價差(MA20-MA5) 連三日縮小
    3. 當前價差 < 1%
    """
    if not quote or not candles or len(candles) < 22:
        return None

    price = quote['close']
    if price <= 0:
        return None

    ma5  = calc_ma(candles, 5)
    ma20 = calc_ma(candles, 20)
    if not ma5 or not ma20 or ma20 == 0:
        return None

    # 條件1
    if ma5 >= ma20:
        return None

    # 條件2: 計算近4個交易日每日MA差值，確認連三日縮小
    # 需要每天都重新計算MA5/MA20
    daily_spreads = []
    for offset in range(4):  # 0=4天前, 1=3天前, 2=2天前, 3=昨天
        slice_end = 20 + offset
        if len(candles) >= slice_end:
            c_slice = candles[:slice_end]
            m5  = calc_ma(c_slice, 5)
            m20 = calc_ma(c_slice, 20)
            if m5 and m20:
                daily_spreads.append((m20 - m5) / m20 * 100)  # 百分比

    if len(daily_spreads) < 4:
        return None

    # 檢查連三日縮小：index 1,2,3 都小於 index 0
    shrinking = all(daily_spreads[i] < daily_spreads[0] for i in range(1, 4))
    if not shrinking:
        return None

    # 條件3: 當前價差 < 1%
    current_spread_pct = (ma20 - ma5) / ma20 * 100
    if current_spread_pct >= 1.0:
        return None

    stop_loss  = round(price * 0.97, 2)
    target     = round(ma20, 2)

    # 信心度
    confidence = 0.70
    if current_spread_pct < 0.5:
        confidence += 0.10
    if price > ma5:
        confidence += 0.10
    confidence = min(confidence, 0.95)

    return {
        'symbol':      symbol,
        'price':       price,
        'ma5':         round(ma5, 2),
        'ma20':        round(ma20, 2),
        'spread_pct': round(current_spread_pct, 3),
        'stop_loss':   stop_loss,
        'target':      target,
        'confidence':  confidence,
    }

# ── 主掃描 ───────────────────────────────────────────────
entries, exits_stop, exits_tgt, watching = [], [], [], []

for code in watchlist:
    quote   = get_quote(code)
    candles = get_daily_candles(code, days=25)

    # 檢查是否在部位中
    pos = next((p for p in positions if p['symbol'] == code), None)

    if pos:
        price = quote['close'] if quote else 0
        if price <= 0:
            continue
        avg_cost = pos['avg_cost']
        stop     = round(avg_cost * 0.97, 2)
        tgt_ma20 = round(calc_ma(candles, 20), 2) if candles else None

        if price <= stop:
            exits_stop.append({'symbol': code, 'price': price, 'entry': avg_cost, 'stop': stop})
        elif tgt_ma20 and price >= tgt_ma20:
            exits_tgt.append({'symbol': code, 'price': price, 'entry': avg_cost, 'target': tgt_ma20})
        continue

    # 評估進場
    sig = evaluate_signal(code, quote, candles)
    if sig:
        if sig['confidence'] >= 0.70:
            entries.append(sig)
        else:
            dist_pct = round((sig['ma20'] - sig['price']) / sig['ma20'] * 100, 2)
            watching.append({'symbol': code, 'price': sig['price'],
                             'ma5': sig['ma5'], 'ma20': sig['ma20'],
                             'ma20_dist': dist_pct})

# ── 輸出 ───────────────────────────────────────────────────
now_str = datetime.now().strftime('%H:%M:%S')
lines = []
lines.append(f"⏰ {now_str} | 掃描 {len(watchlist)} 檔 | 部位 {len(positions)} 檔")

if exits_stop:
    lines.append("")
    lines.append("🛑 【停損訊號】")
    for e in exits_stop:
        lines.append(f"   {e['symbol']} | 現價 {e['price']} | 進場 {e['entry']} | 停損價 {e['stop']} | 市價賣出（停損）")

if exits_tgt:
    lines.append("")
    lines.append("🏠 【目標達成】")
    for e in exits_tgt:
        lines.append(f"   {e['symbol']} | 現價 {e['price']} | 進場 {e['entry']} | 目標 {e['target']} | 市價賣出（目標）")

if entries:
    lines.append("")
    lines.append("🎯 【進場訊號】")
    for e in sorted(entries, key=lambda x: -x['confidence']):
        lines.append(f"   {e['symbol']} | 進場 {e['price']} | 停損 {e['stop_loss']} | 目標 {e['target']} | 信心 {e['confidence']:.0%}")

if watching:
    lines.append("")
    lines.append("👀 【觀望】")
    for w in sorted(watching, key=lambda x: x['ma20_dist'])[:10]:
        lines.append(f"   {w['symbol']} | 現價 {w['price']} | MA5 {w['ma5']} | MA20 {w['ma20']} | 距MA20 {w['ma20_dist']}%")

if not exits_stop and not exits_tgt and not entries and not watching:
    lines.append("")
    lines.append("📊 今日無特殊訊號，市場觀望為主。")

print('\n'.join(lines))
