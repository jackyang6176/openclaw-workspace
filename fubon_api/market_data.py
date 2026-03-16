#!/usr/bin/env python3
"""
富邦證券行情數據獲取工具
獲取K線數據、即時行情、歷史數據
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

class FubonMarketData:
    """富邦行情數據客戶端"""
    
    # 富邦行情 Web API 基礎 URL
    BASE_URL = "https://api.fbs.com.tw/api/v1"
    
    def __init__(self):
        self.token = None
        self.config = {}
        
    def load_env(self) -> bool:
        """載入環境變數"""
        env_path = "/home/admin/.env/fubon.env"
        if not os.path.exists(env_path):
            log(f"❌ 配置檔案不存在：{env_path}")
            return False
        
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    self.config[key] = value
        
        required = ['ACCOUNT', 'FUBON_API_KEY']
        for key in required:
            if key not in self.config:
                log(f"❌ 缺少配置：{key}")
                return False
        return True
    
    def get_intraday_quote(self, symbol: str) -> Optional[Dict]:
        """
        獲取即時行情（Web API）
        無需登入，使用公開 API
        """
        try:
            url = f"{self.BASE_URL}/intraday/quote/{symbol}"
            headers = {
                "Content-Type": "application/json",
                "X-API-KEY": self.config.get('FUBON_API_KEY', '')
            }
            
            log(f"獲取即時行情：{symbol}")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                log(f"✅ 行情獲取成功")
                return data
            else:
                log(f"❌ API 錯誤：{response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            log(f"❌ 請求錯誤：{e}")
            return None
    
    def get_historical_candles(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str,
        timeframe: str = "1D"
    ) -> Optional[List[Dict]]:
        """
        獲取歷史K線數據
        
        Args:
            symbol: 股票代號
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            timeframe: 時間框架 (1D=日線, 1W=週線, 1M=月線)
        """
        try:
            url = f"{self.BASE_URL}/historical/candles/{symbol}"
            headers = {
                "Content-Type": "application/json",
                "X-API-KEY": self.config.get('FUBON_API_KEY', '')
            }
            params = {
                "startDate": start_date,
                "endDate": end_date,
                "timeframe": timeframe
            }
            
            log(f"獲取歷史K線：{symbol} ({start_date} ~ {end_date})")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    log(f"✅ K線獲取成功，共 {len(data)} 筆")
                    return data
                else:
                    log(f"✅ K線獲取成功")
                    return data
            else:
                log(f"❌ API 錯誤：{response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            log(f"❌ 請求錯誤：{e}")
            return None
    
    def get_recent_candles(self, symbol: str, days: int = 30) -> Optional[List[Dict]]:
        """
        獲取最近 N 天的K線數據
        
        Args:
            symbol: 股票代號
            days: 天數（預設30天）
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        return self.get_historical_candles(
            symbol,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
    
    def format_candle_data(self, candles: List[Dict]) -> str:
        """格式化K線數據為表格"""
        if not candles:
            return "無數據"
        
        lines = []
        lines.append(f"{'日期':<12} {'開盤':>8} {'最高':>8} {'最低':>8} {'收盤':>8} {'成交量':>12}")
        lines.append("-" * 70)
        
        for candle in candles[-10:]:  # 只顯示最近10筆
            date = candle.get('date', candle.get('time', 'N/A'))
            open_p = candle.get('open', 0)
            high = candle.get('high', 0)
            low = candle.get('low', 0)
            close = candle.get('close', 0)
            volume = candle.get('volume', 0)
            
            lines.append(f"{date:<12} {open_p:>8.2f} {high:>8.2f} {low:>8.2f} {close:>8.2f} {volume:>12,}")
        
        return "\n".join(lines)
    
    def save_candles_to_json(self, symbol: str, candles: List[Dict], filename: str = None):
        """保存K線數據到 JSON 檔案"""
        if not filename:
            filename = f"candles_{symbol}_{datetime.now().strftime('%Y%m%d')}.json"
        
        filepath = os.path.join(LOG_DIR, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(candles, f, ensure_ascii=False, indent=2)
            log(f"✅ 數據已保存：{filepath}")
            return filepath
        except Exception as e:
            log(f"❌ 保存失敗：{e}")
            return None


def main():
    """主程式"""
    if len(sys.argv) < 2:
        print("""
富邦證券行情數據工具

使用方法：
    python3 market_data.py quote <股票代號>              # 即時行情
    python3 market_data.py candles <股票代號> [天數]      # K線數據
    python3 market_data.py save <股票代號> [天數]         # 保存K線到JSON

範例：
    python3 market_data.py quote 00655L
    python3 market_data.py candles 00655L 30
    python3 market_data.py save 00655L 60
""")
        return 1
    
    command = sys.argv[1].lower()
    
    if len(sys.argv) < 3:
        log("❌ 請指定股票代號")
        return 1
    
    symbol = sys.argv[2]
    
    client = FubonMarketData()
    if not client.load_env():
        return 1
    
    if command == "quote":
        data = client.get_intraday_quote(symbol)
        if data:
            print(json.dumps(data, ensure_ascii=False, indent=2))
    
    elif command == "candles":
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        candles = client.get_recent_candles(symbol, days)
        if candles:
            print(client.format_candle_data(candles))
    
    elif command == "save":
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        candles = client.get_recent_candles(symbol, days)
        if candles:
            client.save_candles_to_json(symbol, candles)
    
    else:
        log(f"❌ 未知命令：{command}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
