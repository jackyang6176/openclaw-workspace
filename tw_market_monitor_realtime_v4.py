#!/usr/bin/env python3
"""
台股盤中即時監控 - 新策略A（MA5-MA20黃金交叉前夕）
市場掃描版本 - 只做分析不下單
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

# ── 常數 ──────────────────────────────────────────────────────────────────────
STOP_LOSS_PCT  = 0.97
MIN_CONFIDENCE = 0.70
FROM_DATE       = '2026-02-01'   # 取K線往前起點

NOW = datetime.datetime.now()
NOW_STR = NOW.strftime('%Y-%m-%d %H:%M')
TS_STR  = NOW.strftime('%H:%M:%S')

# ── 登入富邦 ──────────────────────────────────────────────────────────────────
print(f"\n[{TS_STR}] === 台股策略A市場掃描 {NOW_STR} ===\n")

sdk = FubonSDK()
lr = sdk.login(ACCOUNT, ACCT_PASSWORD, CERT_PATH, CERT_PASSWORD)
if not lr.is_success:
    print("❌ 登入失敗"); sys.exit(1)
print("✅ 富邦登入成功")
sdk.init_realtime()

kline_sdk = FubonKlineSDK()
if not kline_sdk.login():
    print("❌ K線SDK登入失敗"); sdk.logout(); sys.exit(1)
print("✅ K線SDK登入成功\n")

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
        data = kline_sdk.get_historical_candles(code, FROM_DATE, NOW_STR[:10], 'D')
        if not data or len(data) < 22:
            return None
        # 富邦 newest-first，要翻轉
        data = list(reversed(data))
        closes = [float(d['close']) for d in data]
        volumes = [float(d['volume']) for d in data]
        return {'closes': closes, 'volumes': volumes}
    except:
        return None

# ── 策略A 分析（4條件版本）────────────────────────────────────────────────────
def analyze_a_4cond(closes, volumes):
    """
    新策略A（4條件）：
    1. MA5 < MA20
    2. 兩線價差（MA20-MA5）連三日縮小
    3. 20MA > 5MA 且兩線價差 < 1%
    4. 連三日量增
    """
    if not closes or len(closes) < 25:
        return None, "K線不足"
    
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

    # 4條件
    cond1 = ma5 < ma20
    cond2 = len(gaps4) == 4 and gaps4[1] < gaps4[0] and gaps4[2] < gaps4[1] and gaps4[3] < gaps4[2]
    cond3 = ma20 > ma5 and gap < 1.0
    cond4 = len(v4) == 4 and v4[3] > v4[2] and v4[2] > v4[1] and v4[1] > v4[0]

    cnt = sum([cond1, cond2, cond3, cond4])
    confidence = cnt / 4.0

    entry_price = round(closes[-1], 2)
    target = round(ma20, 2)
    stop   = round(entry_price * STOP_LOSS_PCT, 2)

    return {
        'close': entry_price,
        'ma5': round(ma5, 2),
        'ma20': round(ma20, 2),
        'gap': round(gap, 3),
        'cond_count': cnt,
        'cond1': cond1, 'cond2': cond2, 'cond3': cond3, 'cond4': cond4,
        'entry': entry_price,
        'target': target,
        'stop': stop,
        'confidence': confidence,
    }, cnt >= 4, confidence

# ── 主迴圈：取得報價 ─────────────────────────────────────────────────────────
print(f"📡 抓取 {len(ALL_CODES)} 檔即時報價...")
quotes = {}
for code in ALL_CODES:
    q = get_quote(code)
    if q:
        quotes[code] = q
    time.sleep(0.25)

# ── 掃描所有標的 ──────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print(f"📊 市場掃描結果")
print("=" * 80)

header = f"{'標的':<12} {'現價':>10} {'MA20距%':>10} {'MA5':>10} {'MA20':>10} {'GAP%':>8} {'vol比':>8} {'評分':>6}"
print(f"\n{header}")
print("-" * 90)

scan_results = []
strong_signals = []

for code in ALL_CODES:
    name = NAME_MAP.get(code, code)
    q = quotes.get(code, {})
    price = q.get('price', 0)
    
    if not price:
        kl = get_klines(code, 5)
        if kl:
            price = kl['closes'][-1]
    
    if not price:
        continue

    kl = get_klines(code, 25)
    if not kl or len(kl['closes']) < 22:
        continue

    details, passes, conf = analyze_a_4cond(kl['closes'], kl['volumes'])
    if not details:
        continue
    
    ma5 = details['ma5']
    ma20 = details['ma20']
    gap = details['gap']
    cnt = details['cond_count']
    ma20_dist = round((price - ma20) / ma20 * 100, 2) if ma20 else 0
    
    # 計算vol ratio
    avg_vol = sum(kl['volumes'][-20:]) / 20 if len(kl['volumes']) >= 20 else sum(kl['volumes']) / len(kl['volumes'])
    vol_ratio = kl['volumes'][-1] / avg_vol if avg_vol > 0 else 0
    
    if passes:
        signal = "✅ 進場"
    elif cnt >= 3:
        signal = "⚠️ 觀察"
    else:
        signal = "❌ "
    
    print(f"{code:<6} {name:<6} {price:>10.2f} {ma20_dist:>+10.2f} {ma5:>10.2f} {ma20:>10.2f} {gap:>8.3f} {vol_ratio:>8.2f} {cnt:>6}/4 {signal}")
    
    scan_results.append({
        'code': code, 'name': name, 'price': price,
        'ma5': ma5, 'ma20': ma20, 'gap': gap, 'cnt': cnt,
        'ma20_dist': ma20_dist, 'vol_ratio': vol_ratio,
        'signal': signal, 'passes': passes, 'conf': conf,
        'entry': details['entry'], 'stop': details['stop'], 'target': details['target']
    })
    
    if passes or cnt >= 3:
        strong_signals.append(scan_results[-1])

# ── 強烈信號摘要 ──────────────────────────────────────────────────────────────
if strong_signals:
    print(f"\n{'='*80}")
    print(f"🔥 符合策略A標的")
    print(f"{'='*80}")
    for s in sorted(strong_signals, key=lambda x: -x['cnt']):
        print(f"\n📌 {s['code']} {s['name']}")
        print(f"   現價: {s['price']} (MA20距: {s['ma20_dist']:+.2f}%)")
        print(f"   MA5: {s['ma5']} | MA20: {s['ma20']} | GAP: {s['gap']:.3f}%")
        print(f"   成交量比: {s['vol_ratio']:.2f}x")
        print(f"   評分: {s['cnt']}/4")
        print(f"   → 進場價: {s['entry']}")
        print(f"   → 停損價: {s['stop']} (-3%)")
        print(f"   → 目標價: {s['target']} (MA20)")

print(f"\n{'='*80}")
print(f"掃描完成: {NOW_STR}")
print(f"{'='*80}\n")

# ── 帳戶狀態（由 main session 填寫）─────────────────────────────────────────────
print("📋 帳戶狀態：（留空，由 main session 填寫）")

# ── 登出 ─────────────────────────────────────────────────────────────────────
sdk.logout()
kline_sdk.logout()