#!/usr/bin/env python3
"""
台股策略A本地篩選器
=====================
用 TWSE 官方 bulk download（全市場，33,000+檔），本地計算 MA5/MA20，無 API 速率限制
"""

import requests, json, time
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse, sys

TWSE_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
TWSE_PARAMS = {"type": "ALL", "response": "json"}


def fetch_day(ds):
    url = TWSE_URL
    params = dict(TWSE_PARAMS, date=ds)
    try:
        r = requests.get(url, params=params, timeout=10)
        j = r.json()
        result = {}
        for t in j.get("tables", []):
            if "每日收盤行情" in t.get("title", ""):
                for row in t["data"]:
                    code = str(row[0]).strip()
                    if len(row) >= 9:
                        try:
                            close = float(str(row[8]).replace(",", ""))
                        except:
                            close = None
                        if close is not None:
                            result[code] = {"date": ds, "close": close}
                break
        return ds, result
    except Exception as e:
        return ds, {}


def last_trading_days(n=25):
    days = []
    d = date.today()
    while len(days) < n:
        d -= timedelta(days=1)
        ds = d.strftime("%Y%m%d")
        params = dict(TWSE_PARAMS, date=ds)
        try:
            r = requests.get(TWSE_URL, params=params, timeout=5)
            j = r.json()
            for t in j.get("tables", []):
                if "每日收盤行情" in t.get("title", "") and t.get("data"):
                    days.append(ds)
                    break
        except:
            pass
    return days


def analyze(stock_closes, trading_dates):
    """分析單一股票的策略A信號"""
    if len(stock_closes) < 20:
        return None
    closes = [stock_closes.get(d) for d in trading_dates]
    if None in closes or len([c for c in closes if c is not None]) < 20:
        return None

    ma5 = sum(closes[-5:]) / 5
    ma20 = sum(closes[-20:]) / 20
    gap_now = (ma20 - ma5) / ma20 * 100 if ma20 else None

    # 近4日gap序列
    valid_gaps = []
    for offset in range(-4, 0):
        i = trading_dates.index(trading_dates[offset]) if trading_dates[offset] in stock_closes else None
        if i is not None and i >= 19:
            m5 = sum(closes[i-4:i+1]) / 5
            m20 = sum(closes[i-19:i+1]) / 20
            if m20:
                valid_gaps.append((m20 - m5) / m20 * 100)

    cond1 = ma5 < ma20
    cond2 = len(valid_gaps) >= 3 and valid_gaps[-1] < valid_gaps[-2] < valid_gaps[-3]
    cond3 = gap_now is not None and 0 < gap_now < 1.0
    cond4 = False  # TWSE bulk 無成交量

    ok = cond1 and cond2 and cond3
    confidence = (int(cond1) + int(cond2) + int(cond3) + int(cond4)) / 4 * 100

    return {
        "ma5": round(ma5, 2),
        "ma20": round(ma20, 2),
        "gap_now": round(gap_now, 3) if gap_now is not None else None,
        "gap_seq": [round(g, 3) for g in valid_gaps[-4:]] if valid_gaps else [],
        "cond1": cond1,
        "cond2": cond2,
        "cond3": cond3,
        "cond4": cond4,
        "confidence": round(confidence, 1),
        "ok": ok,
    }


def screen(trading_dates, candidates=None):
    print(f"下載 {len(trading_dates)} 天 TWSE bulk 資料...", file=sys.stderr)
    all_data = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(fetch_day, d) for d in trading_dates]
        for future in as_completed(futures):
            ds, result = future.result()
            for code, v in result.items():
                if code not in all_data:
                    all_data[code] = {}
                all_data[code][ds] = v["close"]

    print(f"取得 {len(all_data)} 檔股票", file=sys.stderr)
    codes = candidates if candidates else list(all_data.keys())
    results = []
    for code in codes:
        if code not in all_data:
            continue
        sig = analyze(all_data[code], trading_dates)
        if sig:
            results.append({"code": code, **sig})

    results.sort(key=lambda x: -x["confidence"])
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=25)
    parser.add_argument("--codes", type=str, default="", help="逗號分隔股票代碼")
    args = parser.parse_args()

    print(f"抓取最近 {args.days} 個交易日...", file=sys.stderr)
    days = last_trading_days(args.days)
    print(f"交易日: {days[0]} ~ {days[-1]}（共{len(days)}天）", file=sys.stderr)

    candidates = [c.strip() for c in args.codes.split(",")] if args.codes else None
    results = screen(days, candidates)

    print(f"\n{'='*65}")
    print(f"  策略A篩選  {date.today()}  ({len(days)}交易日)")
    print(f"{'='*65}")

    passed = [r for r in results if r["ok"]]
    near = [r for r in results if not r["ok"]]

    print(f"\n【完全符合 3/3 條件】({len(passed)}檔)")
    if passed:
        for r in passed:
            gap_str = "->".join(str(g) for g in r["gap_seq"])
            print(f"  {r['code']}: MA5={r['ma5']} MA20={r['ma20']} gap={r['gap_now']}% [{gap_str}] conf={r['confidence']}%")
    else:
        print("  無")

    print(f"\n【接近符合】（前30檔，缺1-3條件）")
    for r in near[:30]:
        missing = []
        if not r["cond1"]: missing.append("MA5>MA20")
        if not r["cond2"]: missing.append("三日未收斂")
        if not r["cond3"]: missing.append(f"差{r['gap_now']}%")
        if not r["cond4"]: missing.append("量未確認")
        print(f"  {r['code']}: gap={r['gap_now']}% conf={r['confidence']}% 缺{' '.join(missing)}")

    # JSON
    out = {"date": str(date.today()), "trading_days": len(days), "passed": passed, "near": near[:100]}
    with open("/tmp/strategy_a_result.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
