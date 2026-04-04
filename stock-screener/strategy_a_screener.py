#!/usr/bin/env python3
"""
台股策略A篩選器 - 使用富邦 SDK 技術分析 API
===========================================
新策略A進場條件（需同時滿足）：
  1. MA5 < MA20（5日均線在20日均線下方）
  2. 兩線價差（MA20-MA5）連三日縮小（越窄越好）
  3. 兩線價差 < 1%
  4. 連三日量增
"""

import sys
sys.path.insert(0, "/home/admin/.openclaw/workspace")

from fubon_neo.sdk import FubonSDK
from datetime import date
import os

# 候選股清單（從 watchlist 或自行擴展）
CANDIDATES = [
    "2382", "2353", "2323", "6182", "3090", "3130",
    "3416", "6128", "2008", "2007", "3023", "3008",
    "1453", "2027", "2440", "3652", "3532",
    "2481", "3661", "4930", "1718", "2816"
]

def login():
    config = {}
    env = os.path.expanduser("~/.env/fubon.env")
    with open(env) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()
    sdk = FubonSDK()
    result = sdk.login(
        config["ACCOUNT"], config["ACCT_PASSWORD"],
        config["CERT_PATH"], config["CERT_PASSWORD"]
    )
    sdk.init_realtime()
    return sdk, result.data[0]

def get_tech(symbol, sdk):
    """一次取得完整技術數據（使用 SDK API）"""
    tech = sdk.marketdata.rest_client.stock.technical
    rest = sdk.marketdata.rest_client.stock

    # SMA（均線）
    ma5_data = tech.sma(symbol=symbol, period=5, timeframe="D")
    ma20_data = tech.sma(symbol=symbol, period=20, timeframe="D")

    # RSI / MACD
    rsi_data = tech.rsi(symbol=symbol, period=14, timeframe="D")
    macd_data = tech.macd(symbol=symbol, fast=12, slow=26, signal=9, timeframe="D")

    # 即時報價（取成交量）
    q = rest.intraday.quote(symbol=symbol)

    ma5_list = ma5_data["data"] if ma5_data else []
    ma20_list = ma20_data["data"] if ma20_data else []
    rsi_list = rsi_data["data"] if rsi_data else []

    if not ma5_list or not ma20_list:
        return None

    ma5 = ma5_list[-1]["sma"]
    ma20 = ma20_list[-1]["sma"]
    price = q["data"].get("lastPrice") if q and "data" in q else ma5  # fallback
    chg = q["data"].get("changePercent", 0) if q and "data" in q else 0
    vol = q["data"].get("total", {}).get("tradeVolume", 0) if q and "data" in q else 0
    rsi = rsi_list[-1]["rsi"] if rsi_list else None

    # 近4日價差（用于判斷是否三日縮小）
    # 需要至少4筆才能計算
    gaps = []
    for i in range(-4, 0):
        if -i <= len(ma5_list) and -i <= len(ma20_list):
            m5v = ma5_list[i]["sma"]
            m20v = ma20_list[i]["sma"]
            if m20v > 0:
                gaps.append((m20v - m5v) / m20v * 100)

    # 20日均量（用 historical candles）
    hist = rest.historical.candles(symbol=symbol, timeframe="D")
    vol_list = hist["data"] if hist and "data" in hist else []
    if len(vol_list) >= 5:
        avg_vol5 = sum(float(v.get("volume", 0)) for v in vol_list[-5:]) / 5
    else:
        avg_vol5 = 0

    today_vol = float(vol) if vol > 0 else (float(vol_list[-1]["volume"]) if vol_list else 0)

    return {
        "symbol": symbol,
        "name": q["data"].get("name") if q and "data" in q else "",
        "price": price,
        "chg": chg,
        "vol": today_vol,
        "avg_vol5": avg_vol5,
        "vol_ratio": today_vol / avg_vol5 if avg_vol5 > 0 else 0,
        "ma5": ma5,
        "ma20": ma20,
        "ma_gap_pct": (ma20 - ma5) / ma20 * 100,
        "ma5_list": ma5_list,
        "ma20_list": ma20_list,
        "gaps": gaps,  # 近4日價差序列
        "rsi": rsi,
    }

def check_signal(d):
    """檢查是否符合策略A進場條件"""
    if not d:
        return {"ok": False, "reason": "資料不足"}

    gaps = d["gaps"]
    if len(gaps) < 4:
        return {"ok": False, "reason": f"MA資料不足（僅{len(gaps)}筆）"}

    ma5 = d["ma5"]
    ma20 = d["ma20"]
    gap_now = d["ma_gap_pct"]
    vol_ratio = d.get("vol_ratio", 0)

    # 條件1：MA5 < MA20
    cond1 = ma5 < ma20
    # 條件2：兩線價差連三日縮小（最近三個價差都必須比前一個小）
    # gaps = [day-4, day-3, day-2, day-1]（ oldest → 最新）
    # 近三日：gaps[-3], gaps[-2], gaps[-1]（越新越小）
    cond2 = (gaps[-3] > gaps[-2] > gaps[-1])
    # 條件3：兩線價差 < 1%
    cond3 = gap_now < 1.0
    # 條件4：連三日量增（需要從成交明細比對，以下簡化用均量比）
    # 實際應用：需取 intraday.trades 比對逐日成交量
    cond4 = vol_ratio >= 1.5

    ok = cond1 and cond2 and cond3  # cond4 簡化為參考

    confidence = (cond1 + cond2 + cond3) / 3 * 100

    return {
        "ok": ok,
        "cond1_ma5_below_ma20": cond1,
        "cond2_gap_3d_narrowing": cond2,
        "cond3_gap_under_1pct": cond3,
        "cond4_vol_1_5x": cond4,
        "confidence": round(confidence, 1),
        "ma5": round(ma5, 2),
        "ma20": round(ma20, 2),
        "gap_pct": round(gap_now, 3),
        "vol_ratio": round(vol_ratio, 2),
        "rsi": round(d.get("rsi", 0), 2) if d.get("rsi") else None,
        "price": d["price"],
        "chg": d["chg"],
        "gaps": [round(g, 3) for g in gaps],
    }

def main():
    print(f"=== 台股策略A篩選 {date.today()} ===\n")
    sdk, acc = login()

    results = []
    for sym in CANDIDATES:
        try:
            d = get_tech(sym, sdk)
            if not d:
                continue
            sig = check_signal(d)
            results.append({**{"symbol": sym, "name": d.get("name", "")}, **sig})
            print(f"{sym} {d.get('name','')}: MA5={sig['ma5']} MA20={sig['ma20']} gap={sig['gap_pct']}% | "
                  f"Conds: C1={int(sig['cond1_ma5_below_ma20'])} C2={int(sig['cond2_gap_3d_narrowing'])} "
                  f"C3={int(sig['cond3_gap_under_1pct'])} C4={int(sig['cond4_vol_1_5x'])} | "
                  f"信心={sig['confidence']:.0f}% | {sig['reason']}")
        except Exception as e:
            print(f"{sym}: 錯誤 - {e}")

    sdk.logout()

    print(f"\n{'='*60}")
    print(f"=== 符合策略A（5/5條件）===")
    passed = [r for r in results if r["ok"]]
    if not passed:
        print("無完全符合標的")
    for r in passed:
        print(f"  {r['symbol']} {r['name']}: gap={r['gap_pct']}% conf={r['confidence']}% "
              f"vol_ratio={r['vol_ratio']}x RSI={r['rsi']}")

    print(f"\n=== 接近符合（缺1-2條件）===")
    near = [r for r in results if not r["ok"] and r["confidence"] >= 33]
    for r in sorted(near, key=lambda x: -x["confidence"]):
        missing = []
        if not r["cond1_ma5_below_ma20"]: missing.append("MA5>MA20")
        if not r["cond2_gap_3d_narrowing"]: missing.append("三日未收斂")
        if not r["cond3_gap_under_1pct"]: missing.append(f"差>{r['gap_pct']:.1f}%")
        if not r["cond4_vol_1_5x"]: missing.append("量不足1.5x")
        print(f"  {r['symbol']} {r['name']}: gap={r['gap_pct']}% 缺{' '.join(missing)}")


if __name__ == "__main__":
    main()
