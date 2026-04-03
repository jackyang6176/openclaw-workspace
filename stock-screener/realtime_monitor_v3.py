#!/usr/bin/env python3
"""
台股盤中監控 - 即時版（每30分鐘執行）
策略A（MA5-MA20黃金交叉前夕）
2026-04-03 14:36
"""
import os, sys, datetime, json, time, math

WORKSPACE = "/home/admin/.openclaw/workspace"
SCREENER_DIR = f"{WORKSPACE}/stock-screener"
FUBON_API_DIR = f"{WORKSPACE}/fubon_api"
os.makedirs(f"{SCREENER_DIR}/output", exist_ok=True)

# ── 載入環境變數 ─────────────────────────────────────────────────────────────
env_path = "/home/admin/.env/fubon.env"
for line in open(env_path):
    if '=' in line and not line.startswith('#'):
        k, v = line.strip().split('=', 1)
        os.environ[k] = v.strip()

ACCOUNT       = os.environ['ACCOUNT']
ACCT_PASSWORD = os.environ['ACCT_PASSWORD']
CERT_PATH     = os.environ['CERT_PATH']
CERT_PASSWORD = os.environ['CERT_PASSWORD']

sys.path.insert(0, FUBON_API_DIR)
from fubon_kline_sdk import FubonKlineSDK
from fubon_neo.sdk import FubonSDK
from fubon_neo._fubon_neo import BSAction, MarketType, TimeInForce, PriceType, OrderType

# ── 常數 ──────────────────────────────────────────────────────────────────────
BUY_LIMIT      = 30_000
STOP_LOSS_PCT  = 0.97
MIN_CONFIDENCE = 0.70
FROM_DATE       = '2026-02-01'   # 取K線往前起點

NOW = datetime.datetime.now()
NOW_STR = NOW.strftime('%Y-%m-%d %H:%M')
TS_STR  = NOW.strftime('%H:%M:%S')

# ── 登入富邦 ──────────────────────────────────────────────────────────────────
print(f"[{TS_STR}] === 策略A 盤中監控 {NOW_STR} ===")

sdk = FubonSDK()
lr = sdk.login(ACCOUNT, ACCT_PASSWORD, CERT_PATH, CERT_PASSWORD)
if not lr.is_success:
    print("❌ 登入失敗"); sys.exit(1)
print("✅ 富邦登入成功")
sdk.init_realtime()

kline_sdk = FubonKlineSDK()
if not kline_sdk.login():
    print("❌ K線SDK登入失敗"); sdk.logout(); sys.exit(1)
print("✅ K線SDK登入成功")

# ── 載入 watchlist.json ───────────────────────────────────────────────────────
wl_path = f"{SCREENER_DIR}/watchlist.json"
with open(wl_path) as f:
    wl_data = json.load(f)

holdings = wl_data.get('holdings', {})
watchlist = wl_data.get('watchlist', [])

NAME_MAP = {w['code']: w.get('name', w['code']) for w in watchlist}
ALL_CODES = list({w['code'] for w in watchlist if w.get('code')})

# ── 即時報價 ─────────────────────────────────────────────────────────────────
def get_quote(code):
    try:
        r = sdk.marketdata.rest_client.stock.intraday.quote(symbol=code)
        if not r:
            return None
        r = dict(r) if hasattr(r, '__iter__') else r
        return {
            'price': r.get('lastPrice') or r.get('closePrice') or 0,
            'volume': r.get('total', {}).get('tradeVolume') if isinstance(r.get('total'), dict) else r.get('total', {}).get('tradeVolume') or 0,
            'high': r.get('highPrice') or 0,
            'low': r.get('lowPrice') or 0,
            'open': r.get('openPrice') or 0,
            'ref': r.get('referencePrice') or 0,
        }
    except Exception as e:
        return None

# ── K線取得（歷史日K） ───────────────────────────────────────────────────────
def get_klines(code, days=30):
    try:
        data = kline_sdk.get_historical_candles(code, FROM_DATE, '2026-04-03', 'D')
        if not data or len(data) < 22:
            return None
        # 富邦 newest-first，要翻轉
        data = list(reversed(data))
        closes = [float(d['close']) for d in data]
        volumes = [float(d['volume']) for d in data]
        return {'closes': closes, 'volumes': volumes}
    except:
        return None

# ── 策略A 分析 ───────────────────────────────────────────────────────────────
def analyze_a(closes, volumes):
    """
    策略A：MA5-MA20黃金交叉前夕
    需：MA5<MA20、價差<1%且收斂中、量增3日
    返回：(pass:bool, confidence:float, details:dict)
    """
    if not closes or len(closes) < 25:
        return False, 0, {}
    c = closes[-1]
    # 取最近25筆（尾端要含今日）
    c25 = closes[-25:] if len(closes) >= 25 else closes
    v25 = volumes[-25:] if len(volumes) >= 25 else volumes

    def ma(arr, n):
        return sum(arr[-n:]) / n

    ma5  = ma(c25, 5)
    ma20 = ma(c25, 20)
    gap  = (ma20 - ma5) / ma20 * 100 if ma20 else 0

    # 近4日（含今日）價差
    gaps = []
    for i in range(len(c25)):
        m5 = sum(c25[max(0,i-4):i+1])/min(5,i+1)
        m20 = sum(c25[max(0,i-19):i+1])/min(20,i+1)
        g = (m20 - m5) / m20 * 100 if m20 else 0
        gaps.append(g)
    gaps4 = gaps[-4:]  # [大前日, 前日, 昨日, 今日]

    # 近4日量
    v4 = v25[-4:]

    # 5條件
    cond1 = ma5 < ma20
    cond2 = len(gaps4) == 4 and gaps4[1] < gaps4[0] and gaps4[2] < gaps4[1] and gaps4[3] < gaps4[2]
    cond3 = gap < 1.0
    cond4 = gap < 1.0
    cond5 = len(v4) == 4 and v4[3] > v4[2] and v4[2] > v4[1] and v4[1] > v4[0]

    cnt = sum([cond1, cond2, cond3, cond4, cond5])
    confidence = cnt / 5.0

    entry_price = round(c, 2)
    target = round(ma20, 2)
    stop   = round(c * STOP_LOSS_PCT, 2)

    return cnt >= 5, confidence, {
        'close': entry_price,
        'ma5': round(ma5, 2),
        'ma20': round(ma20, 2),
        'gap': round(gap, 3),
        'cond_count': cnt,
        'cond1': cond1, 'cond2': cond2, 'cond3': cond3,
        'cond4': cond4, 'cond5': cond5,
        'entry': entry_price,
        'target': target,
        'stop': stop,
    }

# ── 主迴圈：取得報價 ─────────────────────────────────────────────────────────
print(f"📡 抓取 {len(ALL_CODES)} 檔即時報價...")
quotes = {}
for code in ALL_CODES:
    q = get_quote(code)
    if q:
        quotes[code] = q
    time.sleep(0.25)

# ── 有部位的持股：檢查停損/目標 ─────────────────────────────────────────────
print("\n=== 持股檢查 ===")
stop_loss_actions = []
target_actions = []
holdings_list = []

for code, h in holdings.items():
    ep = h.get('entry_price', 0)
    name = NAME_MAP.get(code, code)
    q = quotes.get(code, {})
    price = q.get('price', 0)
    if not price:
        # 嘗試從K線取最近收盤價
        kl = get_klines(code, 5)
        if kl:
            price = kl['closes'][-1]
        else:
            print(f"  ⚠️ {code} {name} 無報價，跳過")
            continue

    stop = round(ep * STOP_LOSS_PCT, 2) if ep else 0
    target = 0  # MA20需要從K線算

    kl = get_klines(code, 25)
    if kl and len(kl['closes']) >= 20:
        ma20 = sum(kl['closes'][-20:]) / 20
        target = round(ma20, 2)
    else:
        target = 0

    stop_pct = round((price - ep) / ep * 100, 2) if ep and ep > 0 else 0
    ma20_dist = round((price - target) / target * 100, 2) if target and target > 0 else 0

    action = None
    if ep > 0 and price <= stop:
        action = 'STOP_LOSS'
        stop_loss_actions.append({'code': code, 'name': name, 'price': price, 'stop': stop, 'entry': ep})
    elif ep > 0 and target > 0 and price >= target:
        action = 'TARGET'
        target_actions.append({'code': code, 'name': name, 'price': price, 'target': target, 'entry': ep})

    holdings_list.append({
        'code': code, 'name': name, 'entry': ep,
        'price': price, 'stop': stop, 'target': target,
        'stop_pct': stop_pct, 'ma20_dist': ma20_dist,
        'action': action,
    })
    print(f"  {'🛑' if action=='STOP_LOSS' else '🏠' if action=='TARGET' else '📌'} {code} {name}: 現價={price} 進場={ep} 停損={stop} 目標={target} ({stop_pct:+.2f}%)")

# ── 執行停損/目標下單 ────────────────────────────────────────────────────────
if stop_loss_actions:
    print(f"\n⚠️ 執行 {len(stop_loss_actions)} 筆停損...")
    for a in stop_loss_actions:
        try:
            order = sdk.order.rest_client.place_order(
                account=sdk.futures.account(),
                action=BSAction.SELL,
                symbol=a['code'],
                quantity=1,
                price_type=PriceType.MARKET,
                order_type=OrderType.ROD,
                market_type=MarketType.TSE,
                time_in_force=TimeInForce.IOC,
                price=0,
            )
            print(f"  🛑 停損卖出 {a['code']} {a['name']} @ 市價")
        except Exception as e:
            print(f"  ❌ 停損失敗 {a['code']}: {e}")

if target_actions:
    print(f"\n🎯 執行 {len(target_actions)} 筆目標...")
    for a in target_actions:
        try:
            order = sdk.order.rest_client.place_order(
                account=sdk.futures.account(),
                action=BSAction.SELL,
                symbol=a['code'],
                quantity=1,
                price_type=PriceType.MARKET,
                order_type=OrderType.ROD,
                market_type=MarketType.TSE,
                time_in_force=TimeInForce.IOC,
                price=0,
            )
            print(f"  🏠 目標卖出 {a['code']} {a['name']} @ 市價")
        except Exception as e:
            print(f"  ❌ 目標失敗 {a['code']}: {e}")

# ── 策略A 進場掃描 ────────────────────────────────────────────────────────────
print("\n=== 策略A 進場掃描 ===")
entry_candidates = []
observe_list = []

for code in ALL_CODES:
    # 跳過已有部位的
    if code in holdings and holdings[code].get('entry_price', 0) > 0:
        continue

    q = quotes.get(code, {})
    price = q.get('price', 0)
    if not price:
        kl = get_klines(code, 5)
        if kl:
            price = kl['closes'][-1]
        else:
            continue

    kl = get_klines(code, 25)
    if not kl or len(kl['closes']) < 22:
        continue

    passes, conf, details = analyze_a(kl['closes'], kl['volumes'])
    name = NAME_MAP.get(code, code)

    if price > 0:
        if passes and conf >= MIN_CONFIDENCE:
            entry_candidates.append({**details, 'code': code, 'name': name, 'price': price, 'confidence': conf})
            print(f"  ✅ {code} {name}: 現價={price} MA5={details['ma5']} MA20={details['ma20']} 差={details['gap']}% ({details['cond_count']}/5) 信心={conf:.2f}")
        elif details.get('cond_count', 0) >= 3:
            # 接近符合，列入觀察
            ma20 = details.get('ma20', 0)
            ma20_dist = round((price - ma20) / ma20 * 100, 2) if ma20 else 0
            observe_list.append({**details, 'code': code, 'name': name, 'price': price, 'ma20_dist': ma20_dist})
            print(f"  👀 {code} {name}: 現價={price} MA20={ma20} 差={details['gap']}% ({details['cond_count']}/5) MA20距={ma20_dist}%")
        else:
            print(f"  ❌ {code} {name}: ({details.get('cond_count',0)}/5)")

    time.sleep(0.3)

# ── 產出摘要 ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"📊 策略A 監控報告 {NOW_STR}")
print("=" * 60)

if entry_candidates:
    print("\n🎯 進場訊號（信心度≥0.70）：")
    for e in sorted(entry_candidates, key=lambda x: -x['confidence']):
        print(f"   {e['code']} | 進場={e['entry']} | 停損={e['stop']} | 目標={e['target']} | 信心={e['confidence']:.2f}")
else:
    print("\n🎯 進場訊號：無")

if stop_loss_actions:
    print("\n🛑 停損觸發：")
    for a in stop_loss_actions:
        print(f"   {a['code']} | 現價={a['price']} | 動作=市價卖出")
else:
    print("\n🛑 停損觸發：無")

if target_actions:
    print("\n🏠 目標觸發：")
    for a in target_actions:
        print(f"   {a['code']} | 現價={a['price']} | 動作=市價卖出")
else:
    print("\n🏠 目標觸發：無")

if observe_list:
    print("\n👀 觀望名單：")
    for o in sorted(observe_list, key=lambda x: x.get('gap', 999)):
        print(f"   {o['code']} | 現價={o['price']} | MA20距={o['ma20_dist']}%")
else:
    print("\n👀 觀望名單：無")

# ── 持股現況 ─────────────────────────────────────────────────────────────────
if holdings_list:
    print("\n💼 持股現況：")
    for h in holdings_list:
        flag = '🛑' if h['action']=='STOP_LOSS' else '🏠' if h['action']=='TARGET' else '📌'
        print(f"   {flag} {h['code']} {h['name']}: 現價={h['price']} 進場={h['entry']} 停損={h['stop']} 目標={h['target']} ({h['stop_pct']:+.2f}%)")

# ── 更新 watchlist.json（update last_seen & price）─────────────────────────────
try:
    for w in watchlist:
        code = w.get('code')
        q = quotes.get(code, {})
        if q:
            w['last_price'] = q.get('price', w.get('last_price', 0))
        w['last_seen'] = '2026-04-03'
    wl_data['last_updated'] = NOW.isoformat()
    with open(wl_path, 'w') as f:
        json.dump(wl_data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ watchlist.json 已更新")
except Exception as e:
    print(f"\n⚠️ watchlist更新失敗: {e}")

# ── 登出 ─────────────────────────────────────────────────────────────────────
sdk.logout()
kline_sdk.logout()
print(f"\n[{TS_STR}] 監控完成")
