#!/usr/bin/env python3
"""台股盤中監控 - 2026-03-31 12:10"""

import os, sys, datetime, requests

env_path = "/home/admin/.env/fubon.env"
with open(env_path) as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            os.environ[k] = v

from fubon_neo._fubon_neo import CoreSDK, Direction, PriceType, OrderType, TimeInForce

ACCOUNT       = os.environ['ACCOUNT']
ACCT_PASSWORD = os.environ['ACCT_PASSWORD']
CERT_PATH     = os.environ['CERT_PATH']
CERT_PASSWORD = os.environ['CERT_PASSWORD']

STRATEGY_A = ['1453', '2027']
WATCH_LIST  = ['2440', '3652', '3532']
ALL_TARGETS = STRATEGY_A + WATCH_LIST
DEMO        = False
MAX_POSITION_NTD = 30_000
STOP_LOSS_PCT   = -5.0
TAKE_PROFIT_PCT =  10.0

results = {}

# ── 登入 ──────────────────────────────────────────────
sdk = CoreSDK()
login_resp = sdk.login(ACCOUNT, ACCT_PASSWORD, CERT_PATH, CERT_PASSWORD)
print(f"[LOGIN] {login_resp}")
acct = login_resp.data[0]

# ── FinMind Historical Data (MA20) ────────────────────
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
            return closes[-20:] if len(closes) >= 20 else closes
    except Exception as e:
        print(f"[WARN] FinMind {stock_no}: {e}")
    return []

candles_data = {}
for code in ALL_TARGETS:
    closes = get_finmind_prices(code)
    ma20 = sum(closes) / len(closes) if len(closes) >= 20 else None
    candles_data[code] = {'closes': closes, 'ma20': ma20}
    print(f"[KLINE] {code} bars={len(closes)} MA20={ma20}")

# ── 即時報價 ────────────────────────────────────────────
for code in ALL_TARGETS:
    resp = sdk.stock.query_symbol_quote(acct, code)
    if resp.is_success and resp.data:
        d = resp.data
        results[code] = {
            'price': d.last_price,
            'open':  d.open_price,
            'high':  d.high_price,
            'low':   d.low_price,
            'volume': d.total_volume,
            'ref':   d.reference_price,     # 昨收/參考價
            'limitup': d.limitup_price,
            'limitdown': d.limitdown_price,
            'chg_pct': (d.last_price - d.reference_price) / d.reference_price * 100 if d.reference_price else None,
        }
        print(f"[QUOTE] {code} last={d.last_price} ref={d.reference_price} chg={results[code]['chg_pct']:.2f}% vol={d.total_volume}")
    else:
        results[code] = {}

# ── 取得當日部位 ───────────────────────────────────────
try:
    inv = sdk.accounting.inventories(ACCOUNT)
    if inv and hasattr(inv, 'data') and inv.data:
        positions = {str(p.stock_no): p for p in inv.data}
        print(f"[POS] {len(positions)} positions: {list(positions.keys())}")
    else:
        positions = {}
except Exception as e:
    print(f"[WARN] 取得部位: {e}")
    positions = {}

# ── 信號評估 ──────────────────────────────────────────
for code in ALL_TARGETS:
    r = results.get(code, {})
    cd = candles_data.get(code, {})
    ma20 = cd.get('ma20')
    price = r.get('price')
    ref = r.get('ref')
    chg_pct = r.get('chg_pct')
    volume = r.get('volume', 0)

    dist_ma20 = (price - ma20) / ma20 * 100 if (price and ma20) else None

    # 信心度
    conf = 0.0
    if price and ma20 and price > ma20: conf += 0.30
    if chg_pct and chg_pct > 0: conf += 0.25
    if volume and volume > 1000: conf += 0.20   # 有成交量
    if dist_ma20 and dist_ma20 > 0: conf += 0.25

    signal = 'BUY' if (price and ma20 and price > ma20 and chg_pct and chg_pct > 0 and conf >= 0.70) else 'WATCH'

    results[code].update({
        'ma20': ma20,
        'dist_ma20': dist_ma20,
        'confidence': min(conf, 1.0),
        'signal': signal,
        'stop_loss': round(price * (1 + STOP_LOSS_PCT/100), 2) if price else None,
        'take_profit': round(price * (1 + TAKE_PROFIT_PCT/100), 2) if price else None,
        'entry_price': price,
        'order_result': '',
    })
    print(f"[{code}] price={price} MA20={ma20} dist={dist_ma20} chg={chg_pct} conf={conf:.0%} sig={signal}")

# ── 下單 (策略A 買入訊號) ───────────────────────────────
for code in STRATEGY_A:
    r = results[code]
    if r.get('signal') == 'BUY' and code not in positions:
        price = r['price']
        shares = min(1, MAX_POSITION_NTD // int(price * 1000)) if price else 0

        if not DEMO and shares > 0:
            try:
                order_resp = sdk.stock.place_order(
                    account=acct,
                    stock_no=code,
                    buy_or_sell=Direction.Buy,
                    price_type=PriceType.Limit,
                    order_type=OrderType.Common,
                    time_in_force=TimeInForce.ROD,
                    qty=shares,
                    price=price,
                    exchange="TAIEX"
                )
                r['order_result'] = f"已下單: {order_resp}"
                print(f"[ORDER] {code} 買入 {shares} 張 @ {price} → {order_resp}")
            except Exception as e:
                r['order_result'] = f"失敗: {e}"
                print(f"[ORDER FAIL] {code}: {e}")
        else:
            r['order_result'] = "DEMO模式或零股"
    else:
        r['order_result'] = "已有部位或無信號"

# ── 原有標的 停損/停利檢查 ─────────────────────────────
for code in WATCH_LIST:
    r = results[code]
    if code in positions:
        p = positions[code]
        try:
            cost = float(p.cost) if hasattr(p, 'cost') and p.cost else r.get('price')
            qty  = int(p.quantity) if hasattr(p, 'quantity') else 1
        except:
            cost = r.get('price')
            qty = 1
        cur = r.get('price') or cost
        pnl = (cur - cost) / cost * 100 if cost else 0
        sl = round(cost * (1 + STOP_LOSS_PCT/100), 2)
        tp = round(cost * (1 + TAKE_PROFIT_PCT/100), 2)

        r['position'] = {'cost': cost, 'qty': qty, 'pnl_pct': pnl, 'stop_loss': sl, 'take_profit': tp}

        if pnl <= STOP_LOSS_PCT:
            r['position']['status'] = 'STOP_LOSS_TRIGGER'
            if not DEMO:
                try:
                    sdk.stock.place_order(
                        account=acct,
                        stock_no=code,
                        buy_or_sell=Direction.Sell,
                        price_type=PriceType.Limit,
                        order_type=OrderType.Common,
                        time_in_force=TimeInForce.ROD,
                        qty=qty,
                        price=cur,
                        exchange="TAIEX"
                    )
                    print(f"[STOP_LOSS] {code} 賣出 {qty} 張 @ {cur}")
                except Exception as e:
                    print(f"[STOP_LOSS FAIL] {code}: {e}")
        elif pnl >= TAKE_PROFIT_PCT:
            r['position']['status'] = 'TAKE_PROFIT_TRIGGER'
        else:
            r['position']['status'] = 'HOLDING'
    else:
        r['position'] = {'status': 'NO_POSITION'}

# ── 產出報告 ────────────────────────────────────────────
print("\n" + "="*55)
print("📊 台股盤中監控報告 - 2026-03-31 12:10")
print("="*55)

print("\n【策略A 明日首選】")
for code in STRATEGY_A:
    r = results.get(code, {})
    sig = r.get('signal', 'N/A')
    price = r.get('price')
    ma20  = r.get('ma20')
    dist  = r.get('dist_ma20')
    conf  = r.get('confidence', 0)
    chg   = r.get('chg_pct', 0) or 0

    if sig == 'BUY':
        print(f"🎯 進場通知 | {code} | 進場價 {r.get('entry_price')} | 停損 {r.get('stop_loss')} | 目標 {r.get('take_profit')} | 信心度 {conf:.0%}")
        print(f"   現價 {price} | MA20 {ma20:.2f} | 偏離 {dist:+.2f}% | 今日 {chg:+.2f}%")
        print(f"   下單結果: {r.get('order_result', 'N/A')}")
    else:
        dist_str = f"{dist:+.2f}%" if dist is not None else "N/A"
        chg_str = f"{chg:+.2f}%" if chg is not None else "N/A"
        print(f"🟡 觀望 | {code} | 現價 {price} | MA20 {f'{ma20:.2f}' if ma20 else 'N/A'} ({dist_str}) | 今日 {chg_str}% | 信心度 {conf:.0%}")

print("\n【原有追蹤標的】")
for code in WATCH_LIST:
    r = results.get(code, {})
    pos = r.get('position', {})
    status = pos.get('status', 'N/A')
    price = r.get('price')

    if status == 'NO_POSITION':
        dist = r.get('dist_ma20')
        chg  = r.get('chg_pct', 0) or 0
        dist_str = f"{dist:+.2f}%" if dist is not None else "N/A"
        chg_str = f"{chg:+.2f}%" if chg is not None else "N/A"
        ma20_str = f"{r.get('ma20'):.2f}" if r.get('ma20') else "N/A"
        print(f"🟡 觀望 | {code} | 現價 {price} | MA20 {ma20_str} ({dist_str}) | 今日 {chg_str}%")
    else:
        pnl = pos.get('pnl_pct', 0) or 0
        print(f"📌 部位監控 | {code} | 現價 {price} | 停損 {pos.get('stop_loss')} | 目標 {pos.get('take_profit')} | 狀態 {status}")
        print(f"   成本 {pos.get('cost')} | 損益 {pnl:+.2f}%")

print("\n" + "="*55)
print(f"監控時間: 2026-03-31 12:10 | 模式: {'真實交易' if not DEMO else 'DEMO'}")
