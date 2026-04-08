#!/usr/bin/env python3
"""
收盤後全市場篩選 Worker
- 執行 full_market_scan.py
- 符合策略A的股票寫入 watchlist
- 只保留最近20檔
"""
import sys, json, os
sys.path.insert(0, '/home/admin/.openclaw/workspace/fubon_sdk_complete')
from fubon_complete import FubonComplete
from datetime import datetime

SCAN_FILE = "/tmp/strategy_a_daily.json"
WATCHLIST_FILE = "/home/admin/.openclaw/workspace/stock-screener/watchlist.json"

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] 收盤後篩選開始")

    fc = FubonComplete()
    fc._load_config()
    fc.login()

    # 讀取篩選結果
    if os.path.exists(SCAN_FILE):
        with open(SCAN_FILE) as f:
            result = json.load(f)
        passed = result.get('passed', [])
        print(f"找到 {len(passed)} 檔符合策略A")
    else:
        print("無篩選結果")
        passed = []

    # 讀取現有 watchlist（只保留策略A_5of5）
    with open(WATCHLIST_FILE) as f:
        wl = json.load(f)

    # 保留其他策略的股票，只更新策略A_5of5
    other_watchlist = [w for w in wl['watchlist'] if w.get('strategy') != '策略A_5of5']

    # 加入新的策略A_5of5（取前20檔）
    new_strategy_a = []
    for p in passed[:20]:
        sym = p['code']
        # 避免重複
        if any(w['code'] == sym for w in other_watchlist):
            continue
        # 取即時報價
        try:
            q = fc.sdk.marketdata.rest_client.stock.intraday.quote(symbol=sym)
            last = q.get('lastPrice', 0) or p.get('last_price', 0)
        except:
            last = p.get('last_price', 0)

        entry = last
        stop = round(entry * 0.95, 2)
        target = round(entry * 1.10, 2)

        new_strategy_a.append({
            "code": sym,
            "name": p.get('name', sym),
            "added_date": str(datetime.now().date()),
            "last_seen": str(datetime.now().date()),
            "days_in_list": 0,
            "pattern": "strategy_a_full_5of5",
            "entry_reason": f"策略A完全5/5：gap={p.get('gap',0):.2f}% MA5<MA20三日收斂",
            "ma5": p.get('ma5', 0),
            "ma20": p.get('ma20', 0),
            "gap_pct": p.get('gap', 0),
            "last_price": last,
            "entry_price": entry,
            "target_price": target,
            "stop_loss": stop,
            "is_holding": False,
            "strategy": "策略A_5of5",
            "note": f"收盤篩選入選 gap={p.get('gap',0):.2f}%"
        })

    # 合併：其他策略 + 新的策略A（前20檔）
    wl['watchlist'] = other_watchlist + new_strategy_a
    wl['last_updated'] = f"{datetime.now().date()}T14:31:00"

    with open(WATCHLIST_FILE, 'w') as f:
        json.dump(wl, f, ensure_ascii=False, indent=2)

    print(f"已更新 watchlist（共 {len(wl['watchlist'])} 檔）")
    print(f"  策略A_5of5: {len(new_strategy_a)} 檔")
    print(f"  其他: {len(other_watchlist)} 檔")

    fc.logout()

if __name__ == "__main__":
    main()
