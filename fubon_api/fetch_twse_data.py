#!/usr/bin/env python3
"""
台股K線數據獲取工具
從台灣證券交易所獲取歷史行情
"""
import os
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# 設定日誌
LOG_DIR = "/home/admin/.openclaw/workspace/fubon_api/logs"
os.makedirs(LOG_DIR, exist_ok=True)

def log(message: str):
    """簡易日誌"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def get_twse_daily_quote(symbol: str, date_str: str) -> Optional[Dict]:
    """
    獲取台灣證券交易所每日收盤行情
    """
    try:
        # 台灣證券交易所 API
        url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY"
        params = {
            'response': 'json',
            'date': date_str,
            'stockNo': symbol
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('stat') == 'OK':
                return data
            else:
                return None
        else:
            return None
            
    except Exception as e:
        log(f"請求錯誤：{e}")
        return None

def get_recent_kline(symbol: str, days: int = 20) -> Optional[List[Dict]]:
    """
    獲取最近 N 個交易日的K線數據
    """
    log(f"獲取 {symbol} 最近 {days} 個交易日數據...")
    
    records = []
    current_date = datetime.now()
    
    # 嘗試獲取最近幾個月的數據
    for month_offset in range(3):  # 嘗試最近3個月
        target_date = current_date - timedelta(days=month_offset * 30)
        date_str = target_date.strftime('%Y%m%d')
        
        data = get_twse_daily_quote(symbol, date_str)
        
        if data and 'data' in data:
            for row in data['data']:
                try:
                    # 解析日期
                    date_parts = row[0].split('/')
                    year = int(date_parts[0]) + 1911  # 民國年轉西元年
                    month = date_parts[1]
                    day = date_parts[2]
                    date_str = f"{year}-{month}-{day}"
                    
                    # 解析價格（移除逗號）
                    open_p = float(row[3].replace(',', ''))
                    high = float(row[4].replace(',', ''))
                    low = float(row[5].replace(',', ''))
                    close = float(row[6].replace(',', ''))
                    volume = int(row[1].replace(',', ''))
                    
                    records.append({
                        'date': date_str,
                        'open': open_p,
                        'high': high,
                        'low': low,
                        'close': close,
                        'volume': volume
                    })
                except Exception as e:
                    continue
    
    # 按日期排序並取最近 days 筆
    records.sort(key=lambda x: x['date'])
    records = records[-days:]
    
    if records:
        log(f"✅ 成功獲取 {len(records)} 筆數據")
        return records
    else:
        log("❌ 無法獲取數據")
        return None

def format_kline_table(data: List[Dict]) -> str:
    """格式化K線數據為表格"""
    if not data:
        return "無數據"
    
    lines = []
    lines.append("\n" + "=" * 105)
    lines.append(f"00887 永豐中國科技50大 - 最近20個交易日K線")
    lines.append("=" * 105)
    lines.append(f"{'日期':<12} {'開盤':>10} {'最高':>10} {'最低':>10} {'收盤':>10} {'漲跌':>15} {'成交量':>20}")
    lines.append("-" * 105)
    
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
        
        lines.append(f"{date:<12} {open_p:>10.2f} {high:>10.2f} {low:>10.2f} {close:>10.2f} {change_str:>20} {volume:>20,}")
        
        prev_close = close
    
    lines.append("=" * 105)
    
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
    
    log(f"查詢 {symbol} 最近 {days} 個交易日K線數據...")
    
    data = get_recent_kline(symbol, days)
    
    if data:
        print(format_kline_table(data))
        save_kline_data(data, symbol)
    else:
        log("❌ 無法獲取數據")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
