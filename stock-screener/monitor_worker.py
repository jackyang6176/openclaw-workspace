#!/usr/bin/env python3
"""
盤中交易監控 Worker（由 Cron 呼叫）
每5分鐘檢查一次，寫入狀態檔
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
    """用 unrealized_gains_and_loses 取得實際持倉"""
    holdings = []
    try:
        result = fc.sdk.accounting.unrealized_gains_and_loses(account=fc.account)
        if result.is_success and result.data:
            for h in result.data:
                sym = str(h.stock_no).strip()
                entry = float(h.cost_price)
                qty = int(h.tradable_qty)
                unreal = float(getattr(h, 'unrealized_profit', 0) or getattr(h, 'unrealized_loss', 0) or 0)
                last_price = entry + unreal / qty if qty > 0 else entry
                stop = round(entry * 0.95, 2)
                target = round(entry * 1.10, 2)
                pnl = (last_price - entry) / entry * 100 if entry > 0 else 0
                action = None
                if last_price <= stop:
                    action = 'STOP_LOSS'
                elif last_price >= target:
                    action = 'TARGET_HIT'
                holdings.append({
                    'code': sym,
                    'entry': entry,
                    'qty': qty,
                    'last': round(last_price, 2),
                    'pnl': round(pnl, 2),
                    'stop': stop,
                    'target': target,
                    'action': action
                })
    except Exception as e:
        print(f"持倉查詢錯誤: {e}")
    return holdings

def check_watchlist(fc, watchlist, holdings_codes):
    """檢查觀察名單進場信號（排除已有持倉的）"""
    signals = []
    for w in watchlist:
        sym = w['code']
        if sym in holdings_codes:
            continue
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
            if cond1 and cond2 and cond3:
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
    holdings_codes = {h['code'] for h in holdings}
    signals = check_watchlist(fc, watchlist, holdings_codes)

    status = {
        'checked_at': now,
        'holdings': holdings,
        'signals': signals,
        'has_action': bool(holdings and any(h.get('action') for h in holdings)) or bool(signals)
    }

    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    print(f"[{now}] 監控完成")
    if holdings:
        for h in holdings:
            act = f"→ {h['action']}" if h.get('action') else ""
            print(f"  持倉 {h['code']}: {h['last']} PnL={h['pnl']:+.2f}% {act}")
    if signals:
        for s in signals[:5]:
            print(f"  進場信號 {s['code']} {s['name']}: gap={s['gap']}%")
    if not status['has_action']:
        print("  無行動")

    fc.logout()

if __name__ == "__main__":
    main()
