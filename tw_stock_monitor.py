#!/usr/bin/env python3
"""
台股盤中監控腳本 - 2026-04-01 11:37
策略A：短線突破進場
"""

import os
import sys
import datetime
import requests

# Load env
env_path = "/home/admin/.env/fubon.env"
for line in open(env_path):
    if '=' in line and not line.startswith('#'):
        k, v = line.strip().split('=', 1)
        os.environ[k] = v.strip()

from fubon_neo.sdk import FubonSDK, Order
from fubon_neo._fubon_neo import BSAction, MarketType, TimeInForce, PriceType, OrderType

ACCOUNT       = os.environ['ACCOUNT']
ACCT_PASSWORD = os.environ['ACCT_PASSWORD']
CERT_PATH     = os.environ['CERT_PATH']
CERT_PASSWORD = os.environ['CERT_PASSWORD']

# Targets
STRATEGY_A = ['1453', '2027']
WATCH_LIST  = ['2440', '3652', '3532']
ALL_TARGETS = STRATEGY_A + WATCH_LIST

BUY_LIMIT = 30000
DEMO_MODE = False
STOP_LOSS_PCT = -5.0
TAKE_PROFIT_PCT = 10.0

print(f"[INIT] Account: {ACCOUNT}")
print(f"[INIT] Demo: {DEMO_MODE}")
print(f"[INIT] Buy Limit: NTD {BUY_LIMIT}")
print(f"[INIT] Targets: {ALL_TARGETS}")

# ==== LOGIN (using FubonSDK) ====
sdk = FubonSDK()
login_resp = sdk.login(ACCOUNT, ACCT_PASSWORD, CERT_PATH, CERT_PASSWORD)
print(f"[LOGIN] {login_resp.is_success}")
if not login_resp.is_success:
    print("🎯 盤中監控 | 系統錯誤 | 無法登入富邦帳戶")
    sys.exit(1)
acct = login_resp.data[0]
sdk.init_realtime()
print(f"[ACCT] {acct}")

# ==== Historical Data (FinMind) for MA20 ====
def get_finmind_prices(stock_no, days=40):
    end   = datetime.date.today().strftime('%Y-%m-%d')
    start = (datetime.date.today() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
    url = 'https://api.finmindtrade.com/api/v4/data'
    params = {
        'dataset': 'TaiwanStockPrice',
        'data_id': stock_no,
        'start_date': start,
        'end_date': end,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            d = resp.json().get('data', [])
            closes = [float(x['close']) for x in d]
            return closes[-25:]
    except Exception as e:
        print(f"[WARN] FinMind {stock_no}: {e}")
    return []

# ==== Positions (using unrealized gains for price info) ====
def get_positions():
    try:
        # unrealized_gains_and_loses: has stock_no, cost_price, unrealized_profit/loss
        inv = sdk.accounting.unrealized_gains_and_loses(acct)
        if inv and hasattr(inv, 'data') and inv.data:
            return {str(p.stock_no): p for p in inv.data}
    except Exception as e:
        print(f"[WARN] Positions (unrealized): {e}")
    # Fallback to inventories
    try:
        inv = sdk.accounting.inventories(acct)
        if inv and hasattr(inv, 'data') and inv.data:
            return {str(p.stock_no): p for p in inv.data}
    except Exception as e:
        print(f"[WARN] Positions (inventory): {e}")
    return {}

# ==== Realtime Quotes ====
def get_quote(code):
    try:
        resp = sdk.stock.query_symbol_quote(acct, code)
        if resp.is_success and resp.data:
            d = resp.data
            return {
                'price': d.last_price,
                'ref': d.reference_price,
                'open': d.open_price,
                'high': d.high_price,
                'low': d.low_price,
                'volume': d.total_volume,
                'chg_pct': (d.last_price - d.reference_price) / d.reference_price * 100 if d.reference_price else 0,
            }
    except Exception as e:
        print(f"[WARN] Quote {code}: {e}")
    return None

# ==== Place Order (using Order object) ====
def place_order(code, price, qty):
    if DEMO_MODE:
        print(f"[DEMO] BUY {qty} @ {price}")
        return "demo"
    try:
        order = Order(
            buy_sell=BSAction.Buy,
            symbol=code,
            quantity=qty,
            market_type=MarketType.Common,
            price_type=PriceType.Limit,
            time_in_force=TimeInForce.ROD,
            order_type=OrderType.Stock,
            price=str(price)  # price must be string
        )
        resp = sdk.stock.place_order(acct, order)
        print(f"[ORDER] {code} x{qty} @ {price} => {resp}")
        return str(resp)
    except Exception as e:
        print(f"[ERROR] Order: {e}")
        return f"error: {e}"

# ==== MAIN ====
positions = get_positions()
print(f"\n[POSITIONS] {list(positions.keys())}")

# Get MA20
print(f"\n[MA20] Fetching...")
candles = {}
for code in ALL_TARGETS:
    closes = get_finmind_prices(code)
    ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
    candles[code] = {'closes': closes, 'ma20': ma20}
    print(f"  {code}: {len(closes)} bars, MA20={ma20}")

# Get quotes
print(f"\n[QUOTES] Fetching realtime...")
quotes = {}
for code in ALL_TARGETS:
    q = get_quote(code)
    quotes[code] = q
    if q:
        print(f"  {code}: price={q['price']} ref={q['ref']} chg={q['chg_pct']:.2f}% vol={q['volume']}")

# ==== EVALUATE ====
results = {}
for code in ALL_TARGETS:
    r = quotes.get(code, {})
    cd = candles.get(code, {})
    ma20 = cd.get('ma20')
    price = r.get('price')
    ref = r.get('ref')
    chg_pct = r.get('chg_pct', 0)
    volume = r.get('volume', 0)

    dist_ma20 = (price - ma20) / ma20 * 100 if (price and ma20) else None

    # Strategy A confidence
    conf = 0.0
    cond1 = price and ma20 and price > ma20
    cond2 = chg_pct and chg_pct > 0
    cond3 = volume and volume > 0

    if cond1: conf += 0.30
    if cond2: conf += 0.25
    if cond3: conf += 0.15
    if dist_ma20 and dist_ma20 > 0: conf += 0.25
    conf = min(conf, 0.95)

    signal = 'WATCH'
    if cond1 and cond2 and conf >= 0.70 and code in STRATEGY_A:
        signal = 'BUY'

    results[code] = {
        'price': price,
        'ma20': ma20,
        'dist_ma20': dist_ma20,
        'chg_pct': chg_pct,
        'volume': volume,
        'confidence': conf,
        'signal': signal,
        'stop_loss': round(price * (1 + STOP_LOSS_PCT/100), 2) if price else None,
        'take_profit': round(price * (1 + TAKE_PROFIT_PCT/100), 2) if price else None,
        'ref': ref,
        'entry_price': price,
        'order_result': '',
    }
    print(f"[{code}] price={price} MA20={ma20} dist={dist_ma20} chg={chg_pct} conf={conf:.0%} sig={signal}")

# ==== ORDERS ====
print(f"\n[ORDERS]")
for code in STRATEGY_A:
    r = results[code]
    if r['signal'] == 'BUY' and code not in positions:
        price = r['price']
        shares = min(1000, BUY_LIMIT // int(price))  # shares = 股數 (1000股=1張)
        shares = shares // 1000 * 1000  # round down to 1000
        if shares >= 1000 and not DEMO_MODE:
            r['order_result'] = place_order(code, price, shares)

# ==== POSITION MONITOR ====
print(f"\n[POSITION MONITOR]")
for code, pos in positions.items():
    q = quotes.get(code, {})
    price = q.get('price') if q else None
    # unrealized_gains: cost_price; inventories: buy_value/buy_filled_qty
    entry_price = 0
    if hasattr(pos, 'cost_price') and pos.cost_price:
        entry_price = float(pos.cost_price)
    elif hasattr(pos, 'buy_value') and hasattr(pos, 'buy_filled_qty') and pos.buy_filled_qty:
        entry_price = float(pos.buy_value) / float(pos.buy_filled_qty)
    if price and entry_price > 0:
        pnl_pct = (price - entry_price) / entry_price * 100
        sl = round(entry_price * (1 + STOP_LOSS_PCT/100), 2)
        tp = round(entry_price * (1 + TAKE_PROFIT_PCT/100), 2)
        status = "正常"
        if pnl_pct <= STOP_LOSS_PCT:
            status = "⚠️ 停損觸發"
        elif pnl_pct >= TAKE_PROFIT_PCT:
            status = "🎯 停利觸發"
        print(f"  {code}: entry={entry_price} cur={price} pnl={pnl_pct:.2f}% SL={sl} TP={tp} => {status}")
        results[code]['pos_pnl'] = pnl_pct
        results[code]['pos_status'] = status

# ==== REPORT ====
now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
print(f"\n{'='*50}")
print(f"📊 盤中監控報告 | {now_str}")
print(f"{'='*50}")

entries = [(c, r) for c, r in results.items() if r.get('signal') == 'BUY']
if entries:
    for code, r in entries:
        print(f"\n🎯 進場通知")
        print(f"  代碼: {code}")
        print(f"  進場價: {r['price']}")
        print(f"  停損: {r['stop_loss']} ({STOP_LOSS_PCT}%)")
        print(f"  目標: {r['take_profit']} (+{TAKE_PROFIT_PCT}%)")
        print(f"  信心度: {r['confidence']:.0%}")
        if r['order_result']:
            print(f"  下單: {r['order_result']}")
else:
    print("\n👀 觀望")
    for code, r in results.items():
        ma_str = f"{r['ma20']:.2f}" if r['ma20'] else "N/A"
        dist_str = f"{r['dist_ma20']:+.2f}%" if r['dist_ma20'] else "N/A"
        print(f"  {code} | 現價: {r['price']} | MA20: {ma_str} | 距MA20: {dist_str} | 信心度: {r['confidence']:.0%}")

pos_items = [(c, r) for c, r in results.items() if c in positions]
if pos_items:
    print(f"\n📋 部位監控")
    for code, r in pos_items:
        pos = positions[code]
        entry_price = float(pos.cost_price) if hasattr(pos, 'cost_price') and pos.cost_price else 0
        if not entry_price and hasattr(pos, 'buy_value') and hasattr(pos, 'buy_filled_qty') and pos.buy_filled_qty:
            entry_price = float(pos.buy_value) / float(pos.buy_filled_qty)
        price = r['price']
        pnl = r.get('pos_pnl', 0)
        sl = round(entry_price * (1 + STOP_LOSS_PCT/100), 2)
        tp = round(entry_price * (1 + TAKE_PROFIT_PCT/100), 2)
        print(f"  {code} | 現價: {price} | 進場: {entry_price} | PnL: {pnl:.2f}% | 停損: {sl} | 目標: {tp} | {r.get('pos_status','正常')}")

sdk.logout()
print(f"\n[DONE]")
