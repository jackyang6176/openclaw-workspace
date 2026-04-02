#!/usr/bin/env python3
"""台股盤中監控腳本 v2 - 2026-04-02"""

import os
import sys
from datetime import datetime, timedelta

env = {}
env_path = os.path.expanduser("~/.env/fubon.env")
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v

ACCOUNT = env.get("ACCOUNT")
ACCT_PASSWORD = env.get("ACCT_PASSWORD")
CERT_PATH = env.get("CERT_PATH")
CERT_PASSWORD = env.get("CERT_PASSWORD")

print(f"[{datetime.now()}] === 台股盤中監控報告 ===")
print(f"登入帳號: {ACCOUNT}")

from fubon_neo.sdk import FubonSDK
import yfinance as yf

STOCKS_STRATEGY_A = ["1453", "2027"]
STOCKS_OTHER = ["2440", "3652", "3532"]
ALL_STOCKS = STOCKS_STRATEGY_A + STOCKS_OTHER

STOCK_NAMES = {
    "1453": "大將",
    "2027": "大成鋼",
    "2440": "太空梭",
    "3652": "精聯",
    "3532": "台勝科"
}

# yfinance ticker mapping
YF_TICKERS = {
    "1453": "1453.TW",
    "2027": "2027.TW",
    "2440": "2440.TW",
    "3652": "3652.TW",
    "3532": "3532.TW",
}

def get_ma20_from_yfinance(symbol):
    """用 yfinance 取 20 日 MA"""
    try:
        tkr = yf.Ticker(YF_TICKERS.get(symbol, f"{symbol}.TW"))
        hist = tkr.history(period="3mo")
        if hist is None or len(hist) < 20:
            return None, None, None
        closes = hist['Close'].tail(20)
        ma20 = round(closes.mean(), 2)
        avg_vol = round(hist['Volume'].tail(20).mean(), 0)
        # 今日量：用今日（未收盤）或昨日
        today_vol = hist['Volume'].iloc[-1] if len(hist) >= 1 else None
        return ma20, int(today_vol) if today_vol else None, int(avg_vol)
    except Exception as e:
        return None, None, None

try:
    sdk = FubonSDK()
    print("✅ SDK 初始化成功")
    
    login_result = sdk.login(ACCOUNT, ACCT_PASSWORD, CERT_PATH, CERT_PASSWORD)
    print(f"登入: is_success={login_result.is_success}")
    
    if not login_result.is_success:
        print(f"❌ 登入失敗")
        sys.exit(1)
    
    accounts = login_result.data
    account = accounts[0] if accounts else None
    sdk.init_realtime()
    print("✅ 行情連線初始化成功")
    print(f"帳戶: {account.account} ({account.name})")
    
except Exception as e:
    print(f"❌ 初始化失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 取得即時報價 (Fubon)
def get_quote(symbol):
    try:
        result = sdk.stock.query_symbol_quote(account, symbol)
        if result.is_success:
            return result.data
        return None
    except:
        return None

# 取得 MA20 (yfinance)
print("\n📊 計算 MA20 (yfinance)...")
ma20_data = {}
volume_data = {}
for sid in ALL_STOCKS:
    ma20, today_vol, avg_vol = get_ma20_from_yfinance(sid)
    ma20_data[sid] = ma20
    volume_data[sid] = (today_vol, avg_vol)
    name = STOCK_NAMES.get(sid, sid)
    if ma20:
        print(f"  {sid} {name}: MA20={ma20}, 今日量={today_vol:,}, 20日均量={avg_vol:,}")
    else:
        print(f"  {sid} {name}: MA20 資料不足")

# 取得即時報價 (Fubon)
print("\n📡 抓取即時報價 (Fubon)...")
quotes = {}
for sid in ALL_STOCKS:
    q = get_quote(sid)
    quotes[sid] = q
    name = STOCK_NAMES.get(sid, sid)
    if q:
        change = q.last_price - q.reference_price
        pct = (change / q.reference_price) * 100
        print(f"  {sid} {name}: 現價={q.last_price}, 參考={q.reference_price}, 漲跌={change:+.2f}({pct:+.2f}%), 量={q.total_volume}")
    else:
        print(f"  {sid} {name}: 無報價")

print()

# ===== 報告 =====
report_time = datetime.now().strftime("%Y-%m-%d %H:%M")
print("=" * 60)
print(f"【台股監控簡報】{report_time}")
print("=" * 60)

# 策略A評估
print("\n🎯 策略A評估 (1453大將、2027大成鋼)")
print("-" * 50)

signals = []

for sid in STOCKS_STRATEGY_A:
    name = STOCK_NAMES[sid]
    q = quotes.get(sid)
    ma20 = ma20_data.get(sid)
    today_vol_yf, avg_vol_yf = volume_data.get(sid, (None, None))
    
    if q is None:
        print(f"\n⚠️ {sid} {name}: 無法取得報價")
        continue
    
    price = q.last_price
    ref_price = q.reference_price
    change = price - ref_price
    pct_change = (change / ref_price) * 100 if ref_price else 0
    dist_ma20 = ((price - ma20) / ma20) * 100 if ma20 else None
    
    # 成交量：用 yfinance（更完整）vs Fugle 即時量
    today_vol = today_vol_yf if today_vol_yf else q.total_volume
    avg_vol = avg_vol_yf if avg_vol_yf else 0
    vol_ratio = (today_vol / avg_vol) if avg_vol and avg_vol > 0 else 0
    
    vol_str = f"{today_vol:,}" if today_vol else "N/A"
    avg_str = f"{avg_vol:,}" if avg_vol else "N/A"
    
    print(f"\n{sid} {name}")
    print(f"  現價: {price} | 漲跌: {change:+.2f} ({pct_change:+.2f}%)")
    print(f"  成交量: {vol_str} | 20日均量: {avg_str} | 比值: {vol_ratio:.2f}x")
    if dist_ma20 is not None:
        print(f"  MA20: {ma20} | 距MA20: {dist_ma20:+.2f}%")
    else:
        print(f"  MA20: N/A (資料不足)")
    
    cond1 = (price > ma20) if ma20 else False
    cond2 = pct_change > 0
    cond3 = vol_ratio > 1.5
    
    if cond1 and cond2 and cond3:
        confidence = min(0.70 + (dist_ma20 / 100) * 0.1 + min((vol_ratio - 1.5) * 0.1, 0.15), 0.95)
        stop_loss = round(price * 0.95, 2)
        target = round(price * 1.10, 2)
        
        print(f"  ✅ 進場信號滿足 (價格>MA20={cond1}, 漲幅>0={cond2}, 量>1.5x={cond3})")
        print(f"  信心度: {confidence:.2f}")
        print(f"  建議進場價: {price} | 停損: {stop_loss} | 目標: {target}")
        
        if confidence >= 0.70:
            signals.append({
                "stock_id": sid,
                "name": name,
                "price": price,
                "stop_loss": stop_loss,
                "target": target,
                "confidence": confidence,
            })
    else:
        reasons = []
        if not cond1: reasons.append("價格<MA20" if ma20 else "MA20不足")
        if not cond2: reasons.append("今日未漲")
        if not cond3: reasons.append(f"量能不足({vol_ratio:.2f}x<1.5x)")
        print(f"  ❌ 觀望 - {' / '.join(reasons)}")

# 原有追蹤標的
print("\n\n📊 原有追蹤標的")
print("-" * 50)
for sid in STOCKS_OTHER:
    name = STOCK_NAMES[sid]
    q = quotes.get(sid)
    ma20 = ma20_data.get(sid)
    today_vol_yf, avg_vol_yf = volume_data.get(sid, (None, None))
    
    if q is None:
        print(f"\n⚠️ {sid} {name}: 無法取得報價")
        continue
    
    price = q.last_price
    ref_price = q.reference_price
    change = price - ref_price
    pct_change = (change / ref_price) * 100 if ref_price else 0
    dist_ma20 = ((price - ma20) / ma20) * 100 if ma20 else None
    today_vol = today_vol_yf if today_vol_yf else q.total_volume
    avg_vol = avg_vol_yf if avg_vol_yf else 0
    vol_ratio = (today_vol / avg_vol) if avg_vol and avg_vol > 0 else 0
    
    print(f"\n{sid} {name}")
    print(f"  現價: {price} | 漲跌: {change:+.2f} ({pct_change:+.2f}%)")
    print(f"  成交量: {today_vol:,} | 20日均量: {avg_vol:,} | 比值: {vol_ratio:.2f}x")
    if dist_ma20 is not None:
        print(f"  MA20: {ma20} | 距MA20: {dist_ma20:+.2f}%")
    else:
        print(f"  MA20: N/A")

# 總結
print("\n" + "=" * 60)
print("【總結】")
print("=" * 60)

if signals:
    print("\n🎯 進場通知:")
    for sig in signals:
        print(f"  | {sig['stock_id']} {sig['name']} | 進場價 {sig['price']} | 停損 {sig['stop_loss']} | 目標 {sig['target']} | 信心度 {sig['confidence']:.2f} |")
else:
    print("\n📋 觀望:")
    for sid in STOCKS_STRATEGY_A:
        name = STOCK_NAMES[sid]
        q = quotes.get(sid)
        ma20 = ma20_data.get(sid)
        if q:
            price = q.last_price
            dist = ((price - ma20) / ma20) * 100 if ma20 else None
            dist_str = f"{dist:+.2f}%" if dist is not None else "N/A"
            print(f"  | {sid} {name} | 現價 {price} | 距MA20 {dist_str} |")

print("\n⚠️ 部位監控: 目前無持倉（需查詢）")
print("⚠️ 風險提醒: 請嚴守停損-5%、目標+10%規則")
print(f"\n報告時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

try:
    sdk.logout()
except:
    pass