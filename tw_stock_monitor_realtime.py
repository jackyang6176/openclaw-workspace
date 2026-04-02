#!/usr/bin/env python3
"""
台股盤中監控 - 策略A（MA5-MA20黃金交叉前夕）修正版
取富邦即時報價計算MA信號，2026-04-02
"""

import os, sys, datetime, math, json, requests

env_path = "/home/admin/.env/fubon.env"
for line in open(env_path):
    if '=' in line and not line.startswith('#'):
        k, v = line.strip().split('=', 1)
        os.environ[k] = v.strip()

from fubon_neo.sdk import FubonSDK
from fubon_neo._fubon_neo import BSAction, MarketType, TimeInForce, PriceType, OrderType

ACCOUNT       = os.environ['ACCOUNT']
ACCT_PASSWORD = os.environ['ACCT_PASSWORD']
CERT_PATH     = os.environ['CERT_PATH']
CERT_PASSWORD = os.environ['CERT_PASSWORD']

BUY_LIMIT     = 30000
STOP_LOSS_PCT = 0.97
MIN_CONFIDENCE = 0.70
WATCH_LIST    = ['2440', '3652', '3532', '1453', '2027', '2008', '2007', '3023', '3008']
NAME_MAP      = {
    '2440': '特宏亨', '3652': '衡成正', '3532': '翔名',
    '1453': '和大', '2027': '食品', '2008': '高興昌',
    '2007': '燁興', '3023': '信邦', '3008': '大立光',
}

ts = datetime.datetime.now().strftime('%H:%M:%S')
print(f"[{ts}] === 策略A 盤中監控 ===")

sdk = FubonSDK()
lr = sdk.login(ACCOUNT, ACCT_PASSWORD, CERT_PATH, CERT_PASSWORD)
if not lr.is_success:
    print("❌ 登入失敗"); sys.exit(1)
acct = lr.data[0]
sdk.init_realtime()

# ── helpers ────────────────────────────────────────────────────────────────
def get_quote_fubon(code):
    try:
        r = sdk.marketdata.rest_client.stock.intraday.quote(symbol=code)
        if r and isinstance(r, dict):
            return {
                'price': r.get('lastPrice') or r.get('closePrice') or 0,
                'volume': r.get('total', {}).get('tradeVolume') or 0,
                'open': r.get('openPrice') or 0,
                'high': r.get('highPrice') or 0,
                'low': r.get('lowPrice') or 0,
                'reference': r.get('referencePrice') or 0,
            }
    except: pass
    return None

def get_finmind_prices(code, days=45):
    end   = datetime.date.today().strftime('%Y-%m-%d')
    start = (datetime.date.today() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
    try:
        r = requests.get('https://api.finmindtrade.com/api/v4/data', params={
            'dataset': 'TaiwanStockPrice', 'data_id': code, 'start_date': start, 'end_date': end
        }, timeout=10)
        if r.status_code == 200:
            d = r.json().get('data', [])
            return [float(x['close']) for x in d]
    except: pass
    return []

def get_finmind_volumes(code, days=10):
    end   = datetime.date.today().strftime('%Y-%m-%d')
    start = (datetime.date.today() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
    try:
        r = requests.get('https://api.finmindtrade.com/api/v4/data', params={
            'dataset': 'TaiwanStockPrice', 'data_id': code, 'start_date': start, 'end_date': end
        }, timeout=10)
        if r.status_code == 200:
            d = r.json().get('data', [])
            return [float(x.get('Trading_Volume', 0)) for x in d[-5:]]
    except: pass
    return []

def ma(data, n):
    if len(data) < n: return None
    return sum(data[-n:]) / n

def evaluate_signal(code, price):
    """策略A黃金交叉前夕信號評估"""
    closes = get_finmind_prices(code, days=45)
    if not closes or len(closes) < 25:
        return None

    ma5_list  = [ma(closes[:i+1], 5)  for i in range(len(closes))]
    ma20_list = [ma(closes[:i+1], 20) for i in range(len(closes))]
    ma5  = ma5_list[-1]
    ma20 = ma20_list[-1]
    if ma5 is None or ma20 is None or ma20 == 0:
        return None

    # 條件1: MA5 < MA20
    if ma5 >= ma20:
        return None

    # 條件3: 價差 < 1%
    gap_pct = (ma20 - ma5) / ma20 * 100
    if gap_pct >= 1.0:
        return None

    # 條件2: 價差連三日縮小
    if len(ma5_list) < 5:
        return None
    g0 = ma20_list[-1] - ma5_list[-1]
    g1 = ma20_list[-2] - ma5_list[-2]
    g2 = ma20_list[-3] - ma5_list[-3]
    g3 = ma20_list[-4] - ma5_list[-4]
    if not (g0 < g1 < g2 < g3):
        return None

    # 條件4: 量增
    vols = get_finmind_volumes(code)
    if len(vols) >= 4:
        avg_vol3 = (vols[-4] + vols[-3] + vols[-2]) / 3
        vol_inc = vols[-1] > avg_vol3
    else:
        vol_inc = True  # 資料不足時跳過

    cond_count = 4 if vol_inc else 3
    confidence = 0.75 + (0.05 if vol_inc else 0)

    return {
        'code': code, 'price': price,
        'ma5': round(ma5, 2), 'ma20': round(ma20, 2),
        'gap_pct': round(gap_pct, 3), 'cond_count': cond_count,
        'confidence': round(confidence, 2), 'vol_inc': vol_inc,
    }

def get_positions():
    try:
        inv = sdk.accounting.unrealized_gains_and_loses(acct)
        if inv and hasattr(inv, 'data') and inv.data:
            return {str(p.stock_no): p for p in inv.data}
    except: pass
    return {}

# ── main ──────────────────────────────────────────────────────────────────
quotes = {}
for code in WATCH_LIST:
    q = get_quote_fubon(code)
    if q: quotes[code] = q

positions = get_positions()

entries, observations, sell_actions = [], [], []

for code, q in quotes.items():
    name  = NAME_MAP.get(code, code)
    price = q['price']
    pos   = positions.get(code)

    if pos:
        # 有持倉
        try:
            cost = float(getattr(pos, 'cost_price', 0) or 0)
        except:
            cost = price
        stop = round(cost * STOP_LOSS_PCT, 2)
        sig  = evaluate_signal(code, price)
        ma20 = sig['ma20'] if sig else None

        if price <= stop:
            sell_actions.append({'code': code, 'name': name, 'price': price,
                                 'action': '停損', 'cost': cost, 'stop': stop})
        elif ma20 and price >= ma20:
            sell_actions.append({'code': code, 'name': name, 'price': price,
                                 'action': '目標', 'cost': cost, 'ma20': ma20})
        else:
            dist = round((price - ma20) / ma20 * 100, 2) if ma20 else 0
            observations.append({
                'symbol': code, 'name': name, 'price': price,
                'cost': cost, 'stop': stop, 'ma20': ma20,
                'ma20_dist_pct': dist, 'action': '續抱'
            })
    else:
        # 無持倉：策略A評估
        sig = evaluate_signal(code, price)
        if sig:
            dist = round((price - sig['ma20']) / sig['ma20'] * 100, 2)
            sig['ma20_dist_pct'] = dist
            if sig['confidence'] >= MIN_CONFIDENCE:
                entries.append(sig)
            else:
                observations.append({
                    'symbol': code, 'name': name, 'price': price,
                    'ma5': sig['ma5'], 'ma20': sig['ma20'],
                    'gap_pct': sig['gap_pct'], 'confidence': sig['confidence'],
                    'cond_count': sig['cond_count'], 'vol_inc': sig['vol_inc'],
                    'ma20_dist_pct': dist
                })
        else:
            closes = get_finmind_prices(code, days=30)
            ma5v = ma(closes[-5:], 5) if len(closes) >= 5 else None
            ma20v = ma(closes[-20:], 20) if len(closes) >= 20 else None
            dist = round((price - ma20v) / ma20v * 100, 2) if ma20v else 0
            gap = round((ma20v - ma5v) / ma20v * 100, 2) if ma20v and ma5v else 0
            observations.append({
                'symbol': code, 'name': name, 'price': price,
                'ma5': round(ma5v, 2) if ma5v else None,
                'ma20': round(ma20v, 2) if ma20v else None,
                'gap_pct': gap, 'ma20_dist_pct': dist
            })

# ── 產出 ──────────────────────────────────────────────────────────────────
out = [f"📊 監控時間：{ts}"]
out.append(f"📋 監控標的：{', '.join(WATCH_LIST)}")

if entries:
    best = sorted(entries, key=lambda x: -x['confidence'])[0]
    code, price = best['code'], best['price']
    stop = round(price * STOP_LOSS_PCT, 2)
    out.append("")
    out.append(f"🎯 進場：{code} {best['name']}")
    out.append(f"   現價：{price} | MA5：{best['ma5']} | MA20：{best['ma20']} | 價差：{best['gap_pct']}%")
    out.append(f"   停損：{stop} | 目標：MA20 {best['ma20']} | 信心度：{best['confidence']:.2f}")
    # 下單
    try:
        order = Order(buy_sell=BSAction.Buy, product_id=code, price=price, quantity=1,
                      market_type=MarketType.Taiwan, price_type=PriceType.Limit,
                      time_in_force=TimeInForce.IOC, order_type=OrderType.Common)
        res = sdk.order.place_order(acct, order)
        out.append(f"   ✅ 買單已送出：{code} x1 @{price} {'成功' if res.is_success else '失敗'}")
    except Exception as e:
        out.append(f"   ⚠️ 下單失敗：{e}")
else:
    out.append("")
    out.append("🎯 進場：無符合策略A標的")

if sell_actions:
    out.append("")
    out.append("🛑 賣出：")
    for s in sell_actions:
        out.append(f"   {s['code']} {s['name']} | 現價 {s['price']} | {s['action']} | 成本 {s.get('cost', '-')}")
        try:
            order = Order(buy_sell=BSAction.Sell, product_id=s['code'], price=s['price'],
                          quantity=1, market_type=MarketType.Taiwan,
                          price_type=PriceType.Market, time_in_force=TimeInForce.IOC,
                          order_type=OrderType.Common)
            res = sdk.order.place_order(acct, order)
            out.append(f"   ✅ 賣單已送出：{s['code']} x1 {'成功' if res.is_success else '失敗'}")
        except Exception as e:
            out.append(f"   ⚠️ 賣單失敗：{e}")

if observations:
    out.append("")
    out.append(f"👀 觀望 ({len(observations)}檔)：")
    for o in observations:
        ma20s  = f"MA20 {o['ma20']}" if 'ma20' in o and o['ma20'] else ""
        dists  = f"距{o['ma20_dist_pct']:+.2f}%" if 'ma20_dist_pct' in o else ""
        gap    = f"價差{o['gap_pct']:.2f}%" if 'gap_pct' in o else ""
        conf   = f"信心{o['confidence']:.2f}" if 'confidence' in o else ""
        action = o.get('action', '')
        stop_s = f"停損{o.get('stop','-')}" if 'stop' in o else ""
        cost_s = f"成本{o.get('cost','-')}" if 'cost' in o else ""
        parts  = [o['symbol'], o['name'], str(o['price']), ma20s, dists, gap, conf, stop_s, cost_s, action]
        out.append("   " + " | ".join(x for x in parts if x))

print("\n".join(out))

# 保存狀態
state = {
    'timestamp': datetime.datetime.now().isoformat(),
    'quotes': {k: {kk:vv for kk,vv in v.items()} for k,v in quotes.items()},
    'entries': entries, 'observations': observations, 'sell_actions': sell_actions,
}
sp = f"/home/admin/.openclaw/workspace/stock-screener/output/realtime_state_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.json"
with open(sp, 'w') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
print(f"\n[SAVED] {sp}")
