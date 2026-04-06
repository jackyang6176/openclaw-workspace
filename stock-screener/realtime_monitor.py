#!/usr/bin/env python3
"""
盤中即時監控 - 新策略A（MA5-MA20黃金交叉前夕）
每30分鐘執行，掃描 watchlist 標的即時報價與 MA 狀態
"""
import os, sys, json, time
from datetime import datetime, date, timedelta

WORKSPACE = "/home/admin/.openclaw/workspace"
FUBON_API_DIR = f"{WORKSPACE}/fubon_api"
OUTPUT_DIR = f"{WORKSPACE}/stock-screener/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
sys.path.insert(0, FUBON_API_DIR)

from fubon_kline_sdk import FubonKlineSDK

STOCK_NAMES = {
    '2330': '台積電', '2317': '鴻海', '2454': '聯發科', '2382': '緯創', '2308': '台達電',
    '2303': '聯電', '3034': '聯詠', '2357': '華碩', '3008': '大立光', '2327': '國巨',
    '3481': '友達', '2353': '宏碁', '2345': '智邦', '2609': '陽明', '2610': '長榮',
    '2323': '中壽', '2325': '矽品', '2344': '華邦電', '2352': '方正', '2360': '鴻準',
    '2379': '瑞昱', '2383': '台光電', '2440': '太空梭', '2498': '宏達電', '3006': '順德',
    '3014': '聯陽', '3031': '佰鴻', '3045': '凌耀', '3090': '日電硝', '3130': '一零',
    '3149': '衡平', '3189': '景碩', '3231': '緯穎', '3257': '虹冠電', '3305': '聚積',
    '3338': '新利虹', '3416': '龍燷', '3443': '創意', '3450': '聯亞', '3504': '昇陽',
    '3532': '台勝科', '3545': '敦泰', '3567': '逸昌', '3576': '新日光', '3583': '辛耘',
    '3587': '闊新', '3593': '保銓', '3594': '淂瑩', '3607': '谷林', '3617': '頎邦',
    '3652': '力致', '3661': '世芯', '3665': '創家', '3673': 'TPK', '3682': '粵海',
    '3698': '上海', '3702': '大聯大', '3706': '永道', '3711': '眾達', '3714': '富邦金',
    '3740': '永固', '2008': '高興昌', '2007': '燁興', '3023': '信邦',
}

PRIORITY_STOCKS = [
    '2330','2317','2454','2382','2308','2303','3034','2357','3008','2327',
    '3481','2353','2345','2609','2610','2323','2325','2344','2352','2360',
    '2379','2383','2440','2498','3006','3014','3031','3045','3090','3130',
    '3149','3189','3231','3257','3305','3416','3443','3450','3504','3532',
    '3545','3661','3673','3682','3711','3714','2008','2007','3023',
]

def get_realtime_price(client, symbol):
    """取盤中即時報價（分K的最後收盤價）"""
    try:
        data = client.get_intraday_candles(symbol, "1")
        if data and len(data) > 0:
            last = data[-1]
            return float(last.get('close', 0)), float(last.get('volume', 0))
    except:
        pass
    return None, None

def get_daily_klines(client, symbol, days=30):
    """取日K"""
    today = date.today().strftime('%Y-%m-%d')
    start = (date.today() - timedelta(days=days+10)).strftime('%Y-%m-%d')
    try:
        data = client.get_historical_candles(symbol, start, today, 'D')
        if data:
            data = list(reversed(data))
            return data
    except:
        pass
    return None

def analyze_ma_signal(klines):
    """
    新策略A信號評估
    條件：
    1. 5MA < 20MA
    2. 兩線價差（20MA-5MA）連三日縮小
    3. 兩線價差 < 1%
    4. 連三日量增
    返回：(信號描述, 等級, 詳細dict)
    """
    if not klines or len(klines) < 25:
        return None

    closes = [float(k['close']) for k in klines]
    volumes = [float(k['volume']) for k in klines]

    n = len(closes)

    # MA5, MA20 列表
    ma5_list, ma20_list, gap_list = [], [], []
    for i in range(n):
        ma5 = sum(closes[max(0,i-4):i+1]) / min(5, i+1)
        ma20 = sum(closes[max(0,i-19):i+1]) / min(20, i+1)
        gap = (ma20 - ma5) / ma20 * 100 if ma20 > 0 else 0
        ma5_list.append(ma5)
        ma20_list.append(ma20)
        gap_list.append(gap)

    # 最近4日 index
    d3, d2, d1, d0 = n-4, n-3, n-2, n-1

    ma5_latest = ma5_list[d0]
    ma20_latest = ma20_list[d0]
    gap_latest = gap_list[d0]

    # 條件評估
    cond1 = ma5_latest < ma20_latest                           # 5MA < 20MA
    cond2 = gap_list[d2] < gap_list[d3] and gap_list[d1] < gap_list[d2] and gap_list[d0] < gap_list[d1]  # 連三日收斂
    cond3 = gap_latest < 1.0                                    # 價差 < 1%
    cond4 = (volumes[d0] > volumes[d1]) and (volumes[d1] > volumes[d2]) and (volumes[d2] > volumes[d3])  # 量增3日

    cnt = sum([cond1, cond2, cond3, cond4])

    close_latest = closes[d0]
    entry_price = close_latest
    target = round(ma20_latest, 2)
    stop = round(entry_price * 0.97, 2)
    ma_dist_pct = (ma20_latest - close_latest) / close_latest * 100  # 現價偏離MA20%

    return {
        'close': close_latest,
        'ma5': round(ma5_latest, 2),
        'ma20': round(ma20_latest, 2),
        'gap_pct': round(gap_latest, 3),
        'ma_dist_pct': round(ma_dist_pct, 2),
        'cond1': cond1, 'cond2': cond2, 'cond3': cond3, 'cond4': cond4,
        'cond_count': cnt,
        'entry_price': entry_price,
        'target': target,
        'stop': stop,
        'vol_today': int(volumes[d0]),
        'vol_d1': int(volumes[d1]),
        'vol_d2': int(volumes[d2]),
        'vol_d3': int(volumes[d3]),
    }

def main():
    now = datetime.now()
    print(f"[{now.strftime('%H:%M:%S')}] === 盤中即時監控啟動 ===")
    print(f"[{now.strftime('%H:%M:%S')}] 新策略A - MA5-MA20黃金交叉前夕")

    # 登入
    client = FubonKlineSDK()
    if not client.login():
        print("❌ 富邦登入失敗")
        return
    print(f"[{now.strftime('%H:%M:%S')}] ✅ 富邦登入成功")

    # 對 PRIORITY_STOCKS 逐檔掃描
    results = []
    total = len(PRIORITY_STOCKS)

    for i, sym in enumerate(PRIORITY_STOCKS):
        sys.stdout.write(f"\r[{now.strftime('%H:%M:%S')}] [{i+1}/{total}] 掃描 {sym}...")
        sys.stdout.flush()

        price, vol = get_realtime_price(client, sym)
        klines = get_daily_klines(client, sym, days=30)

        if klines is None:
            continue

        sig = analyze_ma_signal(klines)
        if sig:
            sig['symbol'] = sym
            sig['name'] = STOCK_NAMES.get(sym, sym)
            sig['realtime_price'] = price
            sig['realtime_vol'] = vol
            results.append(sig)

        time.sleep(0.25)

    client.logout()
    print()

    # 分類輸出
    passed = [r for r in results if r['cond_count'] == 4]
    near = [r for r in results if 2 <= r['cond_count'] <= 3]

    print()
    print("=" * 80)
    print(f"【新策略A 市場掃描】{now.strftime('%Y-%m-%d %H:%M')} (UTC+8)")
    print("=" * 80)

    # 表頭
    print(f"{'標的':<8} {'名稱':<8} {'現價':>8} {'MA20':>8} {'MA20距%':>8} {'滿足':>5} {'信號':<20}")
    print("-" * 80)

    # 完全符合
    if not passed:
        print(f"{'(無)':<8}")
    for r in sorted(passed, key=lambda x: x['ma_dist_pct']):
        print(f"{r['symbol']:<8} {r['name']:<8} {r['close']:>8.2f} {r['ma20']:>8.2f} {r['ma_dist_pct']:>+8.2f}% {r['cond_count']:>5}/4  {'✅完全符合'}")
    print()
    for r in sorted(passed, key=lambda x: x['ma_dist_pct']):
        print(f"  ▶ {r['symbol']} {r['name']} | 進場價 {r['close']:.2f} | 目標(MA20) {r['target']:.2f} | 停損 {r['stop']:.2f} | 現價偏離MA20 {r['ma_dist_pct']:+.2f}%")

    print()
    print(f"📊 接近符合（{len(near)} 檔）")
    print("-" * 80)
    if not near:
        print(f"{'(無)':<8}")
    for r in sorted(near, key=lambda x: (-x['cond_count'], x['gap_pct'])):
        missing = []
        if not r['cond1']: missing.append('MA5≥MA20')
        if not r['cond2']: missing.append('三日未收斂')
        if not r['cond3']: missing.append('差≥1%')
        if not r['cond4']: missing.append('量未增3日')
        signal = '🔸接近(' + str(r['cond_count']) + '/4) ' + ','.join(missing[:2])
        print(f"{r['symbol']:<8} {r['name']:<8} {r['close']:>8.2f} {r['ma20']:>8.2f} {r['ma_dist_pct']:>+8.2f}% {r['cond_count']:>5}/4  {signal}")

    print()
    print("=" * 80)
    print("【策略說明】新策略A：MA5<MA20 + 價差連三日收斂至<1% + 量增三日 → 進場")
    print("停損：-3% | 出場：反彈至MA20")
    print("=" * 80)

    # 保存
    out = {
        'timestamp': now.isoformat(),
        'total_scanned': total,
        'passed': passed,
        'near_miss': near,
    }
    out_file = f"{OUTPUT_DIR}/realtime_scan_{now.strftime('%Y%m%d_%H%M')}.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"💾 結果已保存：{out_file}")

if __name__ == '__main__':
    main()