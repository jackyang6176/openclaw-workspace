#!/usr/bin/env python3
"""
富邦證券歷史K線數據獲取工具
使用 akshare 獲取台股歷史行情數據
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

def get_twse_kline(symbol: str, days: int = 20) -> Optional[List[Dict]]:
    """
    獲取台股歷史K線數據
    使用 akshare 套件
    """
    try:
        import akshare as ak
        
        log(f"獲取 {symbol} 最近 {days} 個交易日數據...")
        
        # 計算日期範圍
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days * 2)  # 乘以2確保獲取足夠交易日
        
        # 使用 akshare 獲取台股歷史數據
        # 台股ETF代號格式：00887
        df = ak.stock_zh_index_daily_em(symbol=f"{symbol}.TW")
        
        if df is None or df.empty:
            log("❌ 無法獲取數據")
            return None
        
        # 轉換為字典列表
        records = []
        for index, row in df.tail(days).iterrows():
            records.append({
                'date': index.strftime('%Y-%m-%d'),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': int(row['volume'])
            })
        
        log(f"✅ 成功獲取 {len(records)} 筆數據")
        return records
        
    except ImportError:
        log("❌ 缺少 akshare 套件，嘗試安裝...")
        os.system("pip install akshare -q")
        return get_twse_kline(symbol, days)
    except Exception as e:
        log(f"❌ 獲取數據失敗：{e}")
        return None

def get_yahoo_kline(symbol: str, days: int = 20) -> Optional[List[Dict]]:
    """
    使用 yfinance 獲取台股數據（備選方案）
    """
    try:
        import yfinance as yf
        
        log(f"使用 Yahoo Finance 獲取 {symbol} 數據...")
        
        # 台股代號格式：00887.TW
        ticker = f"{symbol}.TW"
        stock = yf.Ticker(ticker)
        
        # 獲取歷史數據
        df = stock.history(period=f"{days}d")
        
        if df is None or df.empty:
            log("❌ 無法獲取數據")
            return None
        
        # 轉換為字典列表
        records = []
        for index, row in df.iterrows():
            records.append({
                'date': index.strftime('%Y-%m-%d'),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume'])
            })
        
        log(f"✅ 成功獲取 {len(records)} 筆數據")
        return records
        
    except ImportError:
        log("❌ 缺少 yfinance 套件")
        return None
    except Exception as e:
        log(f"❌ 獲取數據失敗：{e}")
        return None

def format_kline_table(data: List[Dict]) -> str:
    """格式化K線數據為表格"""
    if not data:
        return "無數據"
    
    lines = []
    lines.append("\n" + "=" * 95)
    lines.append(f"{'日期':<12} {'開盤':>10} {'最高':>10} {'最低':>10} {'收盤':>10} {'漲跌':>10} {'成交量':>15}")
    lines.append("-" * 95)
    
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
        
        lines.append(f"{date:<12} {open_p:>10.2f} {high:>10.2f} {low:>10.2f} {close:>10.2f} {change_str:>18} {volume:>15,}")
        
        prev_close = close
    
    lines.append("=" * 95)
    
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

def save_kline_chart(data: List[Dict], symbol: str, filename: str = None):
    """生成簡易K線圖表（文字版）"""
    if not data:
        return
    
    if not filename:
        filename = f"kline_{symbol}_{datetime.now().strftime('%Y%m%d')}.txt"
    
    filepath = os.path.join(LOG_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"{symbol} K線數據\n")
            f.write(f"生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 95 + "\n\n")
            f.write(format_kline_table(data))
        
        log(f"✅ K線圖表已保存：{filepath}")
        return filepath
    except Exception as e:
        log(f"❌ 保存失敗：{e}")
        return None

def main():
    """主程式"""
    if len(sys.argv) < 2:
        print("""
富邦證券歷史K線數據工具

使用方法：
    python3 history_kline.py <股票代號> [天數]

範例：
    python3 history_kline.py 00887 20
    python3 history_kline.py 00655L 30
    python3 history_kline.py 00882 60
""")
        return 1
    
    symbol = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    
    log(f"查詢 {symbol} 最近 {days} 個交易日K線數據...")
    
    # 嘗試獲取數據
    data = None
    
    # 優先使用 akshare
    data = get_twse_kline(symbol, days)
    
    # 如果失敗，嘗試 yfinance
    if not data:
        log("嘗試使用備選方案...")
        data = get_yahoo_kline(symbol, days)
    
    if data:
        print(format_kline_table(data))
        save_kline_chart(data, symbol)
    else:
        log("❌ 無法獲取數據")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
