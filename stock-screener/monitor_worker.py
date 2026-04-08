#!/usr/bin/env python3
"""
盤中交易監控 Worker（由 Cron 呼叫）
每5分鐘檢查一次，不主動回報，只寫入狀態檔
"""
import sys, json
sys.path.insert(0, '/home/admin/.openclaw/workspace/fubon_sdk_complete')
from fubon_complete import FubonComplete
from datetime import datetime

STATUS_FILE = "/tmp/trading_status.json"
WATCHLIST_FILE = "/home/admin/.openclaw/workspace/stock-screener/watchlist.json"

def load_watchlist():
    try:
        with open(WATCHLIST_FILE) as f:
            return json.load(f)['watchlist']
    except:
        return []

def get_holdings(fc):
    """取得已成交的實際持倉（排除未成交訂單）"""
    holdings = {}
    try:
        orders = fc.sdk.stock.get_order_results(account=fc.account)
        if orders.data:
            for o in orders.data:
                sym = getattr(o, 'stock_no', None) or getattr(o, 'symbol', None)
                if not sym:
                    continue
                filled = getattr(o, 'filled_qty', 0) or 0
                qty = getattr(o, 'quantity', 0) or 0
                price = getattr(o, 'price', 0) or 0
                bs = str(getattr(o, 'buy_sell', ''))
                status = getattr(o, 'status', 0) or 0

                if filled and filled > 0 and 'Buy' in bs:
                    # 累計同檔股票的買進數量
                    if sym not in holdings:
                        holdings[sym] = {'qty': 0, 'avg_price': 0, 'price_sum': 0}
                    holdings[sym]['qty'] += filled
                    holdings[sym]['price_sum'] += price * filled
    except:
        pass
    # 計算平均成本
    for sym, h in holdings.items():
        if h['qty'] > 0:
            h['avg_price'] = round(h['price_sum'] / h['qty'], 2)
    return holdings

def check_holdings(fc, holdings):
    """檢查持倉的停損/目標狀態"""
    results = []
    for sym, h in holdings.items():
        try:
            q = fc.sdk.marketdata.rest_client.stock.intraday.quote(symbol=sym)
            last = q.get('lastPrice', 0)
            chg = q.get('changePercent', 0)
            entry = h['avg_price']
            stop = round(entry * 0.95, 2)
            target = round(entry * 1.10, 2)
            pnl = (last - entry) / entry * 100 if entry > 0 else 0
            action = None
            if last <= stop:
                action = 'STOP_LOSS'
            elif last >= target:
                action = 'TARGET_HIT'
            results.append({
                'code': sym,
                'entry': entry,
                'last': last,
                'chg': round(chg, 2),
                'pnl': round(pnl, 2),
                'stop': stop,
                'target': target,
                'action': action
            })
        except:
            pass
    return results

def check_watchlist(fc, watchlist, holdings_codes):
    """檢查觀察名單（排除已有持倉的）"""
    signals = []
    for w in watchlist:
        sym = w['code']
        if sym in holdings_codes:
            continue  # 已在持倉，不重複進場
        try:
            q = fc.sdk.marketdata.rest_client.stock.intraday.quote(symbol=sym)
            last = q.get('lastPrice', 0)
            if not last or last <= 0:
                continue
            sma5 = fc.get_sma(sym, 5)
            sma20 = fc.get_sma(sym, 20)
            if not sma5 or not sma20 or len(sma5) < 5 or len(sma20) < 20:
                continue
            m5 = sma5[-1]['sma']
            m20 = sma20[-1]['sma']
            gap = (m20 - m5) / m20 * 100
            # 三日收斂
            gaps = []
            for offset in range(-3, 0):
                idx5 = len(sma5) + offset
                idx20 = len(sma20) + offset
                if 0 <= idx5 < len(sma5) and 0 <= idx20 < len(sma20):
                    g = (sma20[idx20]['sma'] - sma5[idx5]['sma']) / sma20[idx20]['sma'] * 100
                    gaps.append(g)
            cond1 = m5 < m20
            cond2 = len(gaps) >= 2 and gaps[-1] < gaps[-2]
            cond3 = 0 < gap < 2.0
            entry_ready = cond1 and cond2 and cond3
            if entry_ready:
                signals.append({
                    'code': sym,
                    'name': w.get('name', ''),
                    'price': last,
                    'ma5': round(m5, 2),
                    'ma20': round(m20, 2),
                    'gap': round(gap, 2),
                    'gap_seq': [round(g, 2) for g in gaps],
                    'action': 'ENTRY_SIGNAL'
                })
        except:
            pass
    return signals

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fc = FubonComplete()
    fc._load_config()
    ok = fc.login()
    if not ok:
        print("登入失敗")
        return

    watchlist = load_watchlist()
    holdings = get_holdings(fc)
    holdings_check = check_holdings(fc, holdings)
    holdings_codes = set(holdings.keys())
    watchlist_signals = check_watchlist(fc, watchlist, holdings_codes)

    status = {
        'checked_at': now,
        'holdings': holdings_check,
        'signals': watchlist_signals,
        'has_action': bool(holdings_check and any(h.get('action') for h in holdings_check)) or bool(watchlist_signals)
    }

    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    print(f"[{now}] 監控完成")
    if holdings_check:
        for h in holdings_check:
            act = f"→ {h['action']}" if h.get('action') else ""
            print(f"  持倉 {h['code']}: {h['last']} ({h['chg']:+.2f}%) PnL={h['pnl']:+.2f}% {act}")
    if watchlist_signals:
        for s in watchlist_signals:
            print(f"  進場信號 {s['code']} {s['name']}: gap={s['gap']}%")
    if not status['has_action']:
        print("  無行動")

    fc.logout()

if __name__ == "__main__":
    main()
