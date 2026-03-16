#!/usr/bin/env python3
"""
台股K線數據獲取工具 - Yahoo Finance 版本
"""
import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# 設定日誌
LOG_DIR = "/home/admin/.openclaw/workspace/fubon_api/logs"
os.makedirs(LOG_DIR, exist_ok=True)

def log(message: str):
    """簡易日誌"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def get_yahoo_kline(symbol: str, days: int = 20) -> Optional[List[Dict]]:
    """
    使用 yfinance 獲取台股K線數據
    """
    try:
        import yfinance as yf
        
        log(f"獲取 {symbol} 最近 {days} 個交易日數據...")
        
        # 台股ETF在Yahoo Finance的代號格式
        ticker = yf.Ticker(f"{symbol}.TW")
        
        # 獲取歷史數據
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days * 2)  # 乘以2確保獲取足夠交易日
        
        df = ticker.history(start=start_date, end=end_date)
        
        if df is None or df.empty:
            log("❌ 無法獲取數據")
            return None
        
        # 轉換為字典列表
        records = []
        for index, row in df.iterrows():
            try:
                records.append({
                    'date': index.strftime('%Y-%m-%d'),
                    'open': round(float(row['Open']), 2),
                    'high': round(float(row['High']), 2),
                    'low': round(float(row['Low']), 2),
                    'close': round(float(row['Close']), 2),
                    'volume': int(row['Volume'])
                })
            except Exception as e:
                continue
        
        # 取最近 days 筆
        records = records[-days:]
        
        log(f"✅ 成功獲取 {len(records)} 筆數據")
        return records
        
    except Exception as e:
        log(f"❌ 獲取數據失敗：{e}")
        import traceback
        log(traceback.format_exc())
        return None

def format_kline_table(symbol: str, name: str, data: List[Dict]) -> str:
    """格式化K線數據為表格"""
    if not data:
        return "無數據"
    
    lines = []
    lines.append("\n" + "=" * 110)
    lines.append(f"{symbol} {name} - 最近{len(data)}個交易日K線")
    lines.append("=" * 110)
    lines.append(f"{'日期':<12} {'開盤':>10} {'最高':>10} {'最低':>10} {'收盤':>10} {'漲跌':>18} {'成交量':>20}")
    lines.append("-" * 110)
    
    prev_close = None
    for item in data:
        date = item['date']
        open_p = item['open']
        high = item['high']
        low = item['low']
        close = item['close']
        volume = item['volume']
        
        # 計算漲跌
        if prev_close is not None:
            change = close - prev_close
            change_pct = (change / prev_close) * 100
            change_str = f"{change:+.2f} ({change_pct:+.2f}%)"
        else:
            change_str = "-"
        
        lines.append(f"{date:<12} {open_p:>10.2f} {high:>10.2f} {low:>10.2f} {close:>10.2f} {change_str:>23} {volume:>20,}")
        
        prev_close = close
    
    lines.append("=" * 110)
    
    # 添加統計資訊
    if data:
        first = data[0]
        last = data[-1]
        total_change = last['close'] - first['open']
        total_change_pct = (total_change / first['open']) * 100
        
        lines.append(f"\n📊 區間統計（{data[0]['date']} ~ {data[-1]['date']}）：")
        lines.append(f"   期間漲跌：{total_change:+.2f} ({total_change_pct:+.2f}%)")
        lines.append(f"   最高價：{max(d['high'] for d in data):.2f}")
        lines.append(f"   最低價：{min(d['low'] for d in data):.2f}")
        lines.append(f"   總成交量：{sum(d['volume'] for d in data):,}")
        lines.append(f"   平均成交量：{sum(d['volume'] for d in data) / len(data):,.0f}")
    
    return "\n".join(lines)

def save_kline_data(data: List[Dict], symbol: str):
    """保存K線數據到檔案"""
    if not data:
        return
    
    filename = f"kline_{symbol}_{datetime.now().strftime('%Y%m%d')}.json"
    filepath = os.path.join(LOG_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"✅ 數據已保存：{filepath}")
        return filepath
    except Exception as e:
        log(f"❌ 保存失敗：{e}")
        return None

def main():
    """主程式"""
    if len(sys.argv) < 2:
        symbol = "00887"
        days = 20
    else:
        symbol = sys.argv[1]
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    
    # 股票名稱對照表
    name_map = {
        '00887': '永豐中國科技50大',
        '00655L': '國泰A50正2',
        '00882': '中信中國高股息'
    }
    name = name_map.get(symbol, symbol)
    
    log(f"查詢 {symbol} {name} 最近 {days} 個交易日K線數據...")
    
    data = get_yahoo_kline(symbol, days)
    
    if data:
        print(format_kline_table(symbol, name, data))
        save_kline_data(data, symbol)
    else:
        log("❌ 無法獲取數據")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
