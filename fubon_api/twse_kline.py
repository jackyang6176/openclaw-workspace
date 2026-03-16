#!/usr/bin/env python3
"""
台股K線數據獲取工具
使用 akshare 獲取台股歷史行情
"""
import os
import sys
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# 設定日誌
LOG_DIR = "/home/admin/.openclaw/workspace/fubon_api/logs"
os.makedirs(LOG_DIR, exist_ok=True)

def log(message: str):
    """簡易日誌"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def get_etf_kline(symbol: str, days: int = 20) -> Optional[List[Dict]]:
    """
    獲取台股ETF歷史K線數據
    """
    try:
        import akshare as ak
        
        log(f"獲取 {symbol} 最近 {days} 個交易日數據...")
        
        # 使用 akshare 獲取台股ETF歷史數據
        # 方法1：使用台灣證券交易所每日收盤行情
        df = ak.stock_tw_daily_em()
        
        if df is None or df.empty:
            log("❌ 無法獲取數據")
            return None
        
        # 過濾指定股票
        symbol_col = df.columns[0]  # 通常是 "代碼" 或 "symbol"
        stock_data = df[df[symbol_col] == symbol]
        
        if stock_data.empty:
            log(f"❌ 找不到股票 {symbol} 的數據")
            return None
        
        # 獲取最近 days 筆數據
        stock_data = stock_data.tail(days)
        
        # 轉換為字典列表
        records = []
        for index, row in stock_data.iterrows():
            try:
                # 嘗試不同的欄位名稱
                date_val = row.get('日期', row.get('date', index))
                if hasattr(date_val, 'strftime'):
                    date_str = date_val.strftime('%Y-%m-%d')
                else:
                    date_str = str(date_val)
                
                records.append({
                    'date': date_str,
                    'open': float(row.get('開盤', row.get('open', 0))),
                    'high': float(row.get('最高', row.get('high', 0))),
                    'low': float(row.get('最低', row.get('low', 0))),
                    'close': float(row.get('收盤', row.get('close', 0))),
                    'volume': int(float(row.get('成交量', row.get('volume', 0))))
                })
            except Exception as e:
                log(f"解析數據錯誤：{e}")
                continue
        
        log(f"✅ 成功獲取 {len(records)} 筆數據")
        return records
        
    except Exception as e:
        log(f"❌ 獲取數據失敗：{e}")
        import traceback
        log(traceback.format_exc())
        return None

def get_stock_daily(symbol: str, start_date: str, end_date: str) -> Optional[List[Dict]]:
    """
    獲取台股每日行情（替代方法）
    """
    try:
        import akshare as ak
        
        log(f"獲取 {symbol} 從 {start_date} 到 {end_date} 的數據...")
        
        # 使用台灣證券交易所個股日成交資訊
        df = ak.stock_tw_stock_daily(symbol=symbol, start_date=start_date, end_date=end_date)
        
        if df is None or df.empty:
            log("❌ 無法獲取數據")
            return None
        
        # 轉換為字典列表
        records = []
        for index, row in df.iterrows():
            records.append({
                'date': str(row.get('日期', index)),
                'open': float(row.get('開盤價', 0)),
                'high': float(row.get('最高價', 0)),
                'low': float(row.get('最低價', 0)),
                'close': float(row.get('收盤價', 0)),
                'volume': int(float(row.get('成交股數', 0)))
            })
        
        log(f"✅ 成功獲取 {len(records)} 筆數據")
        return records
        
    except Exception as e:
        log(f"❌ 獲取數據失敗：{e}")
        return None

def format_kline_table(data: List[Dict]) -> str:
    """格式化K線數據為表格"""
    if not data:
        return "無數據"
    
    lines = []
    lines.append("\n" + "=" * 100)
    lines.append(f"{'日期':<12} {'開盤':>10} {'最高':>10} {'最低':>10} {'收盤':>10} {'漲跌':>15} {'成交量':>15}")
    lines.append("-" * 100)
    
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
        
        lines.append(f"{date:<12} {open_p:>10.2f} {high:>10.2f} {low:>10.2f} {close:>10.2f} {change_str:>20} {volume:>15,}")
        
        prev_close = close
    
    lines.append("=" * 100)
    
    # 添加統計資訊
    if data:
        first = data[0]
        last = data[-1]
        total_change = last['close'] - first['open']
        total_change_pct = (total_change / first['open']) * 100
        
        lines.append(f"\n📊 區間統計：")
        lines.append(f"   期間漲跌：{total_change:+.2f} ({total_change_pct:+.2f}%)")
        lines.append(f"   最高價：{max(d['high'] for d in data):.2f}")
        lines.append(f"   最低價：{min(d['low'] for d in data):.2f}")
        lines.append(f"   總成交量：{sum(d['volume'] for d in data):,}")
    
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
        print("""
台股K線數據工具

使用方法：
    python3 twse_kline.py <股票代號> [天數]

範例：
    python3 twse_kline.py 00887 20
    python3 twse_kline.py 00655L 30
    python3 twse_kline.py 00882 60
""")
        return 1
    
    symbol = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    
    log(f"查詢 {symbol} 最近 {days} 個交易日K線數據...")
    
    # 計算日期範圍
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days * 2)
    
    # 嘗試獲取數據
    data = get_stock_daily(
        symbol,
        start_date.strftime('%Y%m%d'),
        end_date.strftime('%Y%m%d')
    )
    
    if not data:
        log("嘗試使用備選方案...")
        data = get_etf_kline(symbol, days)
    
    if data:
        print(format_kline_table(data))
        save_kline_data(data, symbol)
    else:
        log("❌ 無法獲取數據")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
