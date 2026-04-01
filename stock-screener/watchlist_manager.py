#!/usr/bin/env python3
"""
Watchlist Manager - 持續追蹤清單管理系統
========================================
功能：
1. 每次新篩選結果加入清單
2. 與持倉股合併（持倉股優先保留）
3. 限留 20 檔，淘汰弱勢股
4. 記錄每檔入選原因、入選日期、表現

新策略A進場條件（需滿足全部4條件）：
  1. 價格在 MA20 以下
  2. 股價已呈橫盤整理（10日高低差距 < 8%）
  3. 連三日量增（今日 > 昨日 > 前日 > 大前日）
  4. 型態止跌（錘子或多頭吞噬）
出廠：價格反彈至 MA20 獲利了結
停損：進場價 -3%

使用方式：
    python3 watchlist_manager.py --add path/to/results.json
    python3 watchlist_manager.py --show
    python3 watchlist_manager.py --trim  # 手動執行優勝劣汰
"""

import json
import sys
import os
from datetime import datetime, date
from pathlib import Path

WATCHLIST_FILE = Path(__file__).parent / "watchlist.json"
MAX_WATCHLIST = 20


def load_watchlist():
    if WATCHLIST_FILE.exists():
        with open(WATCHLIST_FILE) as f:
            return json.load(f)
    return {
        "holdings": {},
        "watchlist": [],
        "last_updated": ""
    }


def save_watchlist(data):
    data["last_updated"] = datetime.now().isoformat()
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def score_stock(stock):
    """計算股票保留分數（越高越保留）

    新策略A條件（進場需滿足全部4條件）：
      1. 價格在 MA20 以下
      2. 橫盤整理（10日高低差距 < 8%）
      3. 連三日量增
      4. 型態止跌
    """
    score = 0

    # 1. 距MA20（低於MA20越多分數越高，最高20分）
    ma_dist = stock.get("ma_dist_pct", 0)
    if ma_dist is not None and ma_dist < 0:
        score += min(20, abs(ma_dist) * 2)
    elif ma_dist is not None:
        score += max(0, 20 - ma_dist * 2)

    # 2. 橫盤加分（10日高低差距 < 8% 給15分）
    range_pct = stock.get("range_10d_pct", 0)
    if range_pct > 0 and range_pct < 8:
        score += 15
    elif range_pct > 0:
        score += max(0, 15 - (range_pct - 8))

    # 3. 連三日量增（滿足給20分）
    vol_days = stock.get("vol_increase_days", 0)
    if vol_days >= 3:
        score += 20
    elif vol_days == 2:
        score += 10
    elif vol_days == 1:
        score += 5

    # 4. 型態強度（15分）
    pattern = stock.get("pattern", "")
    if "engulfing" in pattern.lower():
        score += 15
    elif "hammer" in pattern.lower():
        score += 12
    else:
        score += 5

    # 5. 已在倉位（+20分）
    sym = stock.get("code", stock.get("symbol", ""))
    if sym in HOLDINGS or stock.get("is_holding", False):
        score += 20

    # 6. 連續在清單天數（越久表現越好，最高+10分）
    days_in_list = stock.get("days_in_list", 0)
    score += min(10, days_in_list)

    return round(score, 1)


def check_entry_signal(stock):
    """檢查是否符合新策略A進場條件"""
    ma_dist = stock.get("ma_dist_pct", 0)
    range_pct = stock.get("range_10d_pct", 0)
    vol_days = stock.get("vol_increase_days", 0)
    pattern = stock.get("pattern", "").lower()

    cond1 = (ma_dist is not None and ma_dist < 0)       # 價格在MA20以下
    cond2 = (range_pct > 0 and range_pct < 8)            # 橫盤整理
    cond3 = (vol_days >= 3)                                 # 連三日量增
    cond4 = ("hammer" in pattern or "engulfing" in pattern)  # 止跌型態

    all_ok = cond1 and cond2 and cond3 and cond4
    confidence = (cond1 + cond2 + cond3 + cond4) / 4 * 100

    return all_ok, confidence, {
        "cond1_below_ma20": cond1,
        "cond2_consolidation": cond2,
        "cond3_vol_increase": cond3,
        "cond4_hammer_engulfing": cond4
    }


HOLDINGS = {}


def add_to_watchlist(new_stocks):
    """加入新候選股至清單"""
    data = load_watchlist()
    existing = {s["code"]: s for s in data["watchlist"]}
    now = date.today().isoformat()

    for s in new_stocks:
        code = s.get("code") or s.get("stock_code", "")
        if not code:
            continue
        if code in existing:
            existing[code]["days_in_list"] = existing[code].get("days_in_list", 0) + 1
            existing[code]["last_seen"] = now
            existing[code]["today_change_pct"] = s.get("today_change_pct", s.get("change_pct", 0))
            existing[code]["ma_dist_pct"] = s.get("ma_dist_pct", s.get("dist_ma", 0))
            existing[code]["vol_ratio"] = s.get("vol_ratio", s.get("volume_ratio", 1.0))
            existing[code]["last_price"] = s.get("close", s.get("last_price", 0))
            existing[code]["pattern"] = s.get("pattern", existing[code].get("pattern", ""))
            existing[code]["range_10d_pct"] = s.get("range_10d_pct", existing[code].get("range_10d_pct", 0))
            existing[code]["vol_increase_days"] = s.get("vol_increase_days", existing[code].get("vol_increase_days", 0))
        else:
            existing[code] = {
                "code": code,
                "name": s.get("name", s.get("stock_name", "")),
                "added_date": now,
                "last_seen": now,
                "days_in_list": 0,
                "pattern": s.get("pattern", ""),
                "entry_reason": s.get("reason", s.get("entry_reason", "")),
                "today_change_pct": s.get("today_change_pct", s.get("change_pct", 0)),
                "ma_dist_pct": s.get("ma_dist_pct", s.get("dist_ma", 0)),
                "vol_ratio": s.get("vol_ratio", s.get("volume_ratio", 1.0)),
                "range_10d_pct": s.get("range_10d_pct", 0),
                "vol_increase_days": s.get("vol_increase_days", 0),
                "last_price": s.get("close", s.get("last_price", 0)),
                "is_holding": code in HOLDINGS
            }

    data["watchlist"] = list(existing.values())
    return data


def trim_watchlist(data):
    """限留20檔，淘汰弱勢股"""
    total_holdings = len([h for h in HOLDINGS.values() if h.get("entry_price", 0) > 0])
    watchlist_only = [s for s in data["watchlist"] if not s.get("is_holding")]
    holdings_in_list = [s for s in data["watchlist"] if s.get("is_holding")]

    for s in watchlist_only:
        s["_score"] = score_stock(s)

    watchlist_only.sort(key=lambda x: x.get("_score", 0), reverse=True)

    slot = max(0, MAX_WATCHLIST - total_holdings - len(holdings_in_list))
    kept = watchlist_only[:slot]
    removed = watchlist_only[slot:]

    data["watchlist"] = holdings_in_list + kept
    data["removed_last"] = [{"code": s["code"], "name": s["name"], "score": s.get("_score", 0)}
                             for s in removed]

    for s in data["watchlist"]:
        s.pop("_score", None)

    return data


def show_watchlist():
    """顯示目前清單，含進場信號評估"""
    data = load_watchlist()
    print(f"\n{'='*80}")
    print(f"  持續追蹤清單  {date.today()}  |  持倉 {len([h for h in HOLDINGS.values() if h.get('entry_price',0)>0])} 檔  |  觀察 {len(data['watchlist'])} 檔")
    print(f"{'='*80}")

    if data["watchlist"]:
        print(f"\n{'代碼':<8}{'名稱':<10}{'分數':<6}{'MA20距':<8}{'橫盤':<7}{'量增':<6}{'型態':<15}{'天':<4}{'信號'}")
        print("-" * 85)
        for s in sorted(data["watchlist"], key=lambda x: score_stock(x), reverse=True):
            sc = score_stock(s)
            ok, conf, conds = check_entry_signal(s)
            sig = f"✅進({conf:.0f}%)" if ok else f"({conf:.0f}%)"
            ma = f"{s.get('ma_dist_pct',0):+.2f}%"
            rng = f"{s.get('range_10d_pct',0):.1f}%" if s.get('range_10d_pct') else "-"
            vol = f"{s.get('vol_increase_days',0)}天"
            print(f"{s['code']:<8}{s.get('name',''):<10}{sc:<6.1f}{ma:<8}{rng:<7}{vol:<6}"
                  f"{s.get('pattern',''):<15}{s.get('days_in_list',0):<4}{sig}")

    if data.get("removed_last"):
        print(f"\n已淘汰：{', '.join([r['code'] for r in data['removed_last']])}")

    print(f"\n更新時間：{data.get('last_updated', 'N/A')}")
    print()
    return data


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--add", help="加入新候選股 JSON 檔案路徑")
    parser.add_argument("--trim", action="store_true", help="執行優勝劣汰")
    parser.add_argument("--show", action="store_true", help="顯示清單")
    args = parser.parse_args()

    if args.add:
        path = Path(args.add)
        if path.exists():
            with open(path) as f:
                new_data = json.load(f)
            new_stocks = new_data.get("stocks", []) or new_data or []
            data = add_to_watchlist(new_stocks)
            data = trim_watchlist(data)
            save_watchlist(data)
            print(f"已加入 {len(new_stocks)} 檔，trim 至 {len(data['watchlist'])} 檔")
        else:
            print(f"檔案不存在: {path}")
    elif args.trim:
        data = load_watchlist()
        data = trim_watchlist(data)
        save_watchlist(data)
        show_watchlist()
    elif args.show or len(sys.argv) == 1:
        show_watchlist()
