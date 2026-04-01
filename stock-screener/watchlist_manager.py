#!/usr/bin/env python3
"""
Watchlist Manager - 持續追蹤清單管理系統
========================================
新策略A進場條件（需滿足全部5條件）：
  1. 5日均線在 20日均線下方
  2. 5MA 與 20MA 價差連三日縮小（收斂中）
  3. 20MA > 5MA（方向未翻轉，差值 < 1%）
  4. 最近交易日：兩線價差 < 1%
  5. 連三日量增（今日 > 昨日 > 前日 > 大前日）
出廠：價格反彈至 MA20 獲利了結
停損：進場價 -3%

使用方式：
    python3 watchlist_manager.py --add path/to/results.json
    python3 watchlist_manager.py --show
    python3 watchlist_manager.py --trim
"""

import json
import sys
from datetime import datetime, date
from pathlib import Path

WATCHLIST_FILE = Path(__file__).parent / "watchlist.json"
MAX_WATCHLIST = 20

# 持倉股（從帳戶讀取）
HOLDINGS = {}

def load_watchlist():
    if WATCHLIST_FILE.exists():
        with open(WATCHLIST_FILE) as f:
            return json.load(f)
    return {"holdings": {}, "watchlist": [], "last_updated": ""}

def save_watchlist(data):
    data["last_updated"] = datetime.now().isoformat()
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def score_stock(stock):
    """計算股票保留分數（越高越保留）"""
    score = 0

    # 1. 5MA-20MA 差值（越接近0（即將黃金交叉）分數越高）
    ma_gap = stock.get("ma_gap_pct", 0)
    if ma_gap is not None and ma_gap < 0:
        # 5MA低於20MA，差值越小（接近0）越好
        score += min(20, abs(ma_gap) * 10 + (1 - abs(ma_gap)) * 5)
    elif ma_gap is not None and ma_gap > 0:
        score += max(0, 15 - ma_gap * 3)

    # 2. 兩線收斂速度（差值減少越多分數越高）
    gap_narrow_days = stock.get("gap_narrow_days", 0)
    if gap_narrow_days >= 3:
        score += 20
    elif gap_narrow_days == 2:
        score += 12
    elif gap_narrow_days == 1:
        score += 6

    # 3. 連三日量增（滿足給20分）
    vol_days = stock.get("vol_increase_days", 0)
    if vol_days >= 3:
        score += 20
    elif vol_days == 2:
        score += 10
    elif vol_days == 1:
        score += 5

    # 4. 兩線差值 < 1%（滿足給15分）
    if ma_gap is not None and abs(ma_gap) < 1:
        score += 15

    # 5. 已在倉位（+20分）
    sym = stock.get("code", "")
    if sym in HOLDINGS or stock.get("is_holding", False):
        score += 20

    # 6. 連續在清單天數（最高+10分）
    days_in_list = stock.get("days_in_list", 0)
    score += min(10, days_in_list)

    return round(score, 1)

def check_entry_signal(stock):
    """檢查是否符合新策略A進場條件"""
    ma_gap = stock.get("ma_gap_pct", 0)
    gap_narrow_days = stock.get("gap_narrow_days", 0)
    vol_days = stock.get("vol_increase_days", 0)

    cond1 = (ma_gap is not None and ma_gap < 0)            # 5MA在20MA下方
    cond2 = (gap_narrow_days >= 3)                           # 差值連三日縮小
    cond3 = (ma_gap is not None and abs(ma_gap) < 1)      # 差值<1%
    cond4 = (vol_days >= 3)                                  # 連三日量增

    all_ok = cond1 and cond2 and cond3 and cond4
    confidence = (cond1 + cond2 + cond3 + cond4) / 4 * 100

    return all_ok, confidence, {
        "cond1_5ma_below_20ma": cond1,
        "cond2_gap_narrow_3d": cond2,
        "cond3_gap_under_1pct": cond3,
        "cond4_vol_up_3d": cond4
    }

def add_to_watchlist(new_stocks):
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
            existing[code].update({
                "today_change_pct": s.get("today_change_pct", s.get("change_pct", 0)),
                "ma_gap_pct": s.get("ma_gap_pct", existing[code].get("ma_gap_pct", 0)),
                "gap_narrow_days": s.get("gap_narrow_days", existing[code].get("gap_narrow_days", 0)),
                "vol_increase_days": s.get("vol_increase_days", existing[code].get("vol_increase_days", 0)),
                "ma5": s.get("ma5", existing[code].get("ma5", 0)),
                "ma20": s.get("ma20", existing[code].get("ma20", 0)),
                "last_price": s.get("close", s.get("last_price", 0)),
                "pattern": s.get("pattern", existing[code].get("pattern", "")),
            })
        else:
            existing[code] = {
                "code": code,
                "name": s.get("name", s.get("stock_name", "")),
                "added_date": now,
                "last_seen": now,
                "days_in_list": 0,
                "pattern": s.get("pattern", ""),
                "entry_reason": s.get("reason", ""),
                "today_change_pct": s.get("today_change_pct", s.get("change_pct", 0)),
                "ma_gap_pct": s.get("ma_gap_pct", 0),
                "gap_narrow_days": s.get("gap_narrow_days", 0),
                "vol_increase_days": s.get("vol_increase_days", 0),
                "ma5": s.get("ma5", 0),
                "ma20": s.get("ma20", 0),
                "last_price": s.get("close", s.get("last_price", 0)),
                "is_holding": code in HOLDINGS
            }

    data["watchlist"] = list(existing.values())
    return data

def trim_watchlist(data):
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
    data = load_watchlist()
    print(f"\n{'='*90}")
    print(f"  持續追蹤清單  {date.today()}  |  持倉 {len([h for h in HOLDINGS.values() if h.get('entry_price',0)>0])} 檔  |  觀察 {len(data['watchlist'])} 檔")
    print(f"{'='*90}")

    if data["watchlist"]:
        print(f"\n{'代碼':<8}{'名稱':<10}{'MA5':<8}{'MA20':<8}{'兩線差%':<8}{'收斂日':<7}{'量增日':<7}{'分數':<6}{'信號'}")
        print("-" * 75)
        for s in sorted(data["watchlist"], key=lambda x: score_stock(x), reverse=True):
            sc = score_stock(s)
            ok, conf, conds = check_entry_signal(s)
            sig = f"✅進({conf:.0f}%)" if ok else f"({conf:.0f}%)"
            ma5 = f"{s.get('ma5',0):.2f}"
            ma20 = f"{s.get('ma20',0):.2f}"
            gap = f"{s.get('ma_gap_pct',0):+.2f}%"
            print(f"{s['code']:<8}{s.get('name',''):<10}{ma5:<8}{ma20:<8}{gap:<8}"
                  f"{s.get('gap_narrow_days',0):<7}{s.get('vol_increase_days',0):<7}{sc:<6.1f}{sig}")

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
