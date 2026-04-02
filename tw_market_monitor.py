#!/usr/bin/env python3
"""台股盤中監控腳本 - 2026-04-02 09:00"""

import os
import json
from datetime import datetime, time

# 讀取環境變數
env = {}
with open(os.path.expanduser("~/.env/fubon.env")) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v

ACCOUNT = env.get("ACCOUNT")
ACCT_PASSWORD = env.get("ACCT_PASSWORD")
API_KEY = env.get("FUBON_API_KEY")
CERT_PATH = env.get("CERT_PATH")
CERT_PASSWORD = env.get("CERT_PASSWORD")

print(f"[{datetime.now()}] === 台股盤中監控報告 ===")
print(f"登入帳號: {ACCOUNT}")
print(f"憑證: {CERT_PATH}")
print()

from fubon.neo import FubonNeo, Mode
from fubon.neo.models import TimeFrame

# 標的清單
STOCKS_STRATEGY_A = ["1453", "2027"]  # 策略A明日首選
STOCKS_OTHER = ["2440", "3652", "3532"]  # 原有追蹤
ALL_STOCKS = STOCKS_STRATEGY_A + STOCKS_OTHER

# 股票名稱對照
STOCK_NAMES = {
    "1453": "大將",
    "2027": "大成鋼",
    "2440": "太空梭",
    "3652": "精聯",
    "3532": "台勝科"
}

try:
    # 初始化 Fubon Neo
    client = FubonNeo(Mode=Mode.RealTime, api_key=API_KEY)
    
    # 登入
    login_result = client.login(account=ACCOUNT, password=ACCT_PASSWORD)
    print(f"登入結果: {login_result}")
    
    # 取得 Token
    token = client.token
    print(f"Token: {token[:20]}..." if token else "No Token")
    print()

except Exception as e:
    print(f"❌ 登入失敗: {e}")
    print("=" * 50)
    print("【台股監控簡報】2026-04-02 09:00")
    print("=" * 50)
    print("⚠️ 富邦 API 連線失敗")
    print(f"錯誤: {e}")
    print("建議: 檢查網路或 API Key 是否有效")
    print()
    import sys
    sys.exit(1)

# 取得報價
def get_realtime_quote(client, stock_id):
    """取得即時報價"""
    try:
        from fubon.neo.models import StockSpot, Condition, ConditionType, ComparisonUnit, Comparison
        stock_spot = StockSpot(stock_id=stock_id)
        result = client.stock.spot(stock_spot)
        return result
    except Exception as e:
        return {"error": str(e), "stock_id": stock_id}

def get_daily_kline(client, stock_id, days=25):
    """取得日K線資料用於計算MA20"""
    try:
        from fubon.neo.models import StockKline, TimeFrame
        stock_kline = StockKline(stock_id=stock_id, time_frame=TimeFrame.Daily)
        result = client.stock.kline(stock_kline)
        if result and hasattr(result, 'data'):
            return result.data[-days:] if len(result.data) >= days else result.data
        return []
    except Exception as e:
        return []

# 取得所有標的報價
print("📡 抓取即時報價中...")
quotes = {}
for sid in ALL_STOCKS:
    q = get_realtime_quote(client, sid)
    quotes[sid] = q
    print(f"  {sid} {STOCK_NAMES.get(sid,'')}: {q}")

print()

# 取得日K線計算MA20
print("📊 計算MA20中...")
ma20_data = {}
for sid in ALL_STOCKS:
    klines = get_daily_kline(client, sid, 25)
    if klines and len(klines) >= 20:
        closes = [k.close if hasattr(k, 'close') else k.get('close', 0) for k in klines[-20:]]
        ma20 = sum(closes) / 20
        ma20_data[sid] = round(ma20, 2)
        print(f"  {sid} {STOCK_NAMES.get(sid,'')}: MA20={ma20_data[sid]}")
    else:
        ma20_data[sid] = None
        print(f"  {sid} {STOCK_NAMES.get(sid,'')}: K線資料不足")

print()

# 策略A進場評估
print("=" * 50)
print("【台股監控簡報】2026-04-02 09:00")
print("=" * 50)

def parse_quote(q):
    """解析報價結果"""
    if isinstance(q, dict) and "error" in q:
        return None
    if hasattr(q, 'data') and q.data:
        d = q.data[0] if isinstance(q.data, list) else q.data
        return d
    return None

# 評估策略A信號
print("\n🎯 策略A評估 (1453大將、2027大成鋼)")
print("-" * 50)

strategy_a_signals = []
for sid in STOCKS_STRATEGY_A:
    name = STOCK_NAMES[sid]
    q_data = parse_quote(quotes.get(sid))
    ma20 = ma20_data.get(sid)
    
    if q_data is None or ma20 is None:
        print(f"⚠️ {sid} {name}: 資料不足，觀望")
        continue
    
    # 取得報價欄位
    try:
        price = float(q_data.close if hasattr(q_data, 'close') else q_data.get('close', 0))
        change = float(q_data.change if hasattr(q_data, 'change') else q_data.get('change', 0))
        volume = float(q_data.total_volume if hasattr(q_data, 'total_volume') else q_data.get('totalVolume', 0))
        avg_volume = float(q_data.avg_volume if hasattr(q_data, 'avg_volume') else q_data.get('avgVolume', 0)) if hasattr(q_data, 'avg_volume') or 'avgVolume' in q_data else 0
    except:
        print(f"⚠️ {sid} {name}: 資料解析失敗")
        continue
    
    pct_change = (change / (price - change)) * 100 if price != change else 0
    dist_ma20 = ((price - ma20) / ma20) * 100
    
    print(f"\n{sid} {name}")
    print(f"  現價: {price} | 漲跌: {change:+.2f} ({pct_change:+.2f}%)")
    print(f"  成交量: {volume:,.0f} | 均量: {avg_volume:,.0f}")
    print(f"  MA20: {ma20} | 距MA20: {dist_ma20:+.2f}%")
    
    # 策略A條件：價格>MA20 AND 今日漲幅>0% AND 成交量>均量1.5倍
    cond1 = price > ma20
    cond2 = pct_change > 0
    cond3 = avg_volume > 0 and volume > avg_volume * 1.5
    
    if cond1 and cond2 and cond3:
        confidence = min(0.70 + (dist_ma20 / 100) * 0.1 + (volume/(avg_volume*2)) * 0.1, 0.95)
        stop_loss = round(price * 0.95, 2)
        target = round(price * 1.10, 2)
        
        print(f"  ✅ 進場信號滿足")
        print(f"  信心度: {confidence:.2f}")
        print(f"  建議進場價: {price} | 停損: {stop_loss} | 目標: {target}")
        
        strategy_a_signals.append({
            "stock_id": sid,
            "name": name,
            "price": price,
            "stop_loss": stop_loss,
            "target": target,
            "confidence": confidence,
            "dist_ma20": dist_ma20,
            "volume_ratio": volume / avg_volume if avg_volume > 0 else 0
        })
    else:
        reasons = []
        if not cond1: reasons.append("價格<MA20")
        if not cond2: reasons.append("今日未漲")
        if not cond3: reasons.append("量能不足")
        print(f"  ❌ 觀望 - {' / '.join(reasons)}")

# 原有追蹤標的
print("\n\n📊 原有追蹤標的")
print("-" * 50)
for sid in STOCKS_OTHER:
    name = STOCK_NAMES[sid]
    q_data = parse_quote(quotes.get(sid))
    ma20 = ma20_data.get(sid)
    
    if q_data is None:
        print(f"\n⚠️ {sid} {name}: 無法取得報價")
        continue
    
    try:
        price = float(q_data.close if hasattr(q_data, 'close') else q_data.get('close', 0))
        change = float(q_data.change if hasattr(q_data, 'change') else q_data.get('change', 0))
    except:
        print(f"\n⚠️ {sid} {name}: 資料解析失敗")
        continue
    
    pct_change = (change / (price - change)) * 100 if price != change else 0
    dist_ma20 = ((price - ma20) / ma20) * 100 if ma20 else 0
    
    print(f"\n{sid} {name}")
    print(f"  現價: {price} | 漲跌: {change:+.2f} ({pct_change:+.2f}%)")
    print(f"  MA20: {ma20 or 'N/A'} | 距MA20: {dist_ma20:+.2f}%")

# 總結
print("\n" + "=" * 50)
print("【總結】")
print("=" * 50)

if strategy_a_signals:
    print("\n🎯 進場通知:")
    for sig in strategy_a_signals:
        if sig['confidence'] >= 0.70:
            print(f"  | {sig['stock_id']} {sig['name']} | 進場價 {sig['price']} | 停損 {sig['stop_loss']} | 目標 {sig['target']} | 信心度 {sig['confidence']:.2f} |")
else:
    print("\n📋 觀望:")
    for sid in STOCKS_STRATEGY_A:
        name = STOCK_NAMES[sid]
        q_data = parse_quote(quotes.get(sid))
        ma20 = ma20_data.get(sid)
        if q_data:
            try:
                price = float(q_data.close if hasattr(q_data, 'close') else q_data.get('close', 0))
            except:
                price = "N/A"
            dist = ((price - ma20) / ma20) * 100 if isinstance(price, float) and ma20 else "N/A"
            print(f"  | {sid} {name} | 現價 {price} | 距MA20 {dist:.2f}% |" if isinstance(dist, float) else f"  | {sid} {name} | 現價 {price} |")

print("\n⚠️ 部位監控: 目前無持倉")
print("⚠️ 風險提醒: 請嚴守停損-5%、目標+10%規則")
print(f"\n報告時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
