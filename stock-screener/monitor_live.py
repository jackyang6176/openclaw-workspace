#!/usr/bin/env python3
"""
盤中即時監控 - 用 TWSE 前日資料 + quote 即時價
========================================
策略：用 TWSE bulk 取得前交易日收盤價，
配合 quote 即時價當今日參考，本地計算 MA。
"""
import sys, json, os, time
sys.path.insert(0, '/home/admin/.openclaw/workspace/fubon_sdk_complete')
from fubon_complete import FubonComplete
from datetime import date

STATE_FILE = "/tmp/monitor_state.json"
WATCHLIST   = "/home/admin/.openclaw/workspace/stock-screener/watchlist.json"
TWSE_URL    = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"

def fetch_twse_prices(targets):
    """用 TWSE 取得所有股票的近5日收盤價（前交易日，晚盤用）"""
    # 找出最近有資料的交易日
    for days_back in range(1, 10):
        from datetime import date, timedelta
        d = date.today() - timedelta(days=days_back)
        ds = d.strftime("%Y%m%d")
        params = {"date": ds, "type": "ALLBUT0999NOTIND", "response": "json"}
        try:
            import requests
            r = requests.get(TWSE_URL, params=params, timeout=8)
            j = r.json()
            result = {}
            for t in j.get("tables", []):
                if t.get("data") and len(t["data"]) > 100:
                    for row in t["data"]:
                        code = str(row[0]).strip()
                        if code in targets:
                            try:
                                close = float(str(row[8]).replace(",", ""))
                                result[code] = {"date": ds, "close": close}
                            except: continue
                    break
            if result:
                return ds, result
        except: continue
    return None, {}

def get_ma_from_twse(twse_prices):
    """用TWSE近5日收盤計算MA"""
    if len(twse_prices) < 20:
        return None
    closes = [v['close'] for v in twse_prices]
    ma5 = sum(closes[:5]) / 5
    ma20 = sum(closes) / 20
    gap = (ma20 - ma5) / ma20 * 100
    # 近4日gap
    gaps = []
    for i in range(4):
        c4 = closes[i:i+20]
        if len(c4) == 20:
            m5 = sum(c4[:5]) / 5
            m20 = sum(c4) / 20
            gaps.append((m20 - m5) / m20 * 100)
    cond1 = ma5 < ma20
    cond2 = len(gaps) >= 3 and gaps[-1] < gaps[-2] < gaps[-3]
    cond3 = 0 < gap < 2.0
    return {
        'ma5': round(ma5, 2), 'ma20': round(ma20, 2),
        'gap': round(gap, 3), 'gap_seq': [round(g, 2) for g in gaps[-4:]],
        'cond1': cond1, 'cond2': cond2, 'cond3': cond3,
        'signal': cond1 and cond2 and cond3
    }

def get_quote_ma(fc, sym, prev_closes):
    """用 SDK quote 當今日即時價，計算 MA"""
    try:
        q = fc.sdk.marketdata.rest_client.stock.intraday.quote(symbol=sym)
        today_close = q.get('lastPrice', q.get('closePrice', 0))
        ref = q.get('referencePrice', 0)
        chg_pct = q.get('changePercent', 0)
        open_p = q.get('openPrice', 0)
        high = q.get('highPrice', 0)
        low = q.get('lowPrice', 0)
        vol_data = q.get('total', {}) or {}
        vol = vol_data.get('tradeVolume', 0) or 0

        # 合併今日（quote 即時）和前日 TWSE 收盤
        if prev_closes and len(prev_closes) >= 19:
            all_closes = [today_close] + prev_closes[:19]
            ma5 = sum(all_closes[:5]) / 5
            ma20 = sum(all_closes[:20]) / 20
            gap = (ma20 - ma5) / ma20 * 100
            gaps = []
            for i in range(4):
                c4 = all_closes[i:i+20]
                if len(c4) == 20:
                    m5 = sum(c4[:5]) / 5
                    m20 = sum(c4) / 20
                    gaps.append((m20 - m5) / m20 * 100)
            cond1 = ma5 < ma20
            cond2 = len(gaps) >= 3 and gaps[-1] < gaps[-2] < gaps[-3]
            cond3 = 0 < gap < 2.0
            return {
                'last': today_close, 'ref': ref,
                'open': open_p, 'high': high, 'low': low,
                'chg_pct': chg_pct,
                'volume': vol,
                'ma5': round(ma5, 2), 'ma20': round(ma20, 2),
                'gap': round(gap, 3),
                'gap_seq': [round(g, 2) for g in gaps[-4:]],
                'cond1': cond1, 'cond2': cond2, 'cond3': cond3,
                'signal': cond1 and cond2 and cond3
            }
        return None
    except:
        return None

def main():
    today = str(date.today())
    print(f"[{today}] === 盤中即時監控 ===")

    fc = FubonComplete()
    fc._load_config()
    fc.login()

    with open(WATCHLIST) as f:
        wl = json.load(f)

    targets_code = {w['code'] for w in wl['watchlist'] if w.get('strategy') == '策略A_5of5'}
    target_names = {w['code']: w['name'] for w in wl['watchlist'] if w.get('strategy') == '策略A_5of5'}

    # 取 TWSE 前交易日收盤價
    twse_date, twse_prices = fetch_twse_prices(targets_code)
    print(f"TWSE資料: {twse_date}")

    state = {"last_check": today, "prices": {}}
    alerts = []

    for sym in sorted(targets_code):
        # TWSE 前日 MA
        twse_data = {sym: twse_prices[sym]} if sym in twse_prices else None
        ma_info = get_ma_from_twse(list(twse_prices.values()) if twse_prices else [])

        # SDK quote 即時價 + 本地 MA
        qma = get_quote_ma(fc, sym, list(twse_prices.values()) if twse_prices else [])

        if qma:
            last = qma['last']
            ref = qma['ref']
            chg = qma['chg_pct']
            ma5 = qma['ma5']
            ma20 = qma['ma20']
            gap = qma['gap']
            gs = '->'.join([str(g) for g in qma['gap_seq']])
            sig = qma['signal']
            vol = qma['volume']

            # 判斷
            entry_ready = sig
            touched_ma20 = last >= ma20 * 0.99

            if sig:
                status = "✅ 進場訊號"
            elif touched_ma20:
                status = "🔔 接近MA20"
            elif last < ref * 0.97:
                status = "⚠️ 跌破-3%"
            else:
                status = "🟢 正常追蹤"

            print(f"  {sym} {target_names[sym]}: last={last} ({chg:+.2f}%) | MA5={ma5} MA20={ma20} gap={gap}% [{gs}] | {status}")

            state['prices'][sym] = {
                'last': last, 'chg_pct': chg,
                'ma5': ma5, 'ma20': ma20, 'gap': gap,
                'signal': entry_ready, 'vol': vol
            }

            if entry_ready:
                alerts.append(f"✅ {sym} {target_names[sym]}: gap={gap}% MA5<MA20 三日收斂 現價={last} MA20={ma20}")

            time.sleep(2)
        else:
            print(f"  {sym}: 資料不足（TWSE={bool(twse_prices.get(sym))})")

    print(f"\n[{today}] 監控完成")
    if alerts:
        print("🚨 進場訊號:")
        for a in alerts:
            print(f"  {a}")

    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

    fc.logout()

if __name__ == "__main__":
    main()
