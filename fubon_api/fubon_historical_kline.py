#!/usr/bin/env python3
"""
富邦證券歷史K線數據獲取工具
使用富邦 Web API + API Key
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

class FubonHistoricalData:
    """富邦證券歷史數據客戶端"""
    
    # 富邦行情 API 基礎 URL（測試環境）
    BASE_URL = "https://api.fbs.com.tw/api/v1"
    
    def __init__(self):
        self.api_key = None
        self.access_token = None
        
    def load_api_key(self) -> bool:
        """載入 API Key"""
        env_path = "/home/admin/.env/fubon.env"
        if not os.path.exists(env_path):
            log(f"❌ 配置檔案不存在：{env_path}")
            return False
        
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    if key == 'FUBON_API_KEY':
                        self.api_key = value
                        return True
        
        log("❌ 找不到 FUBON_API_KEY")
        return False
    
    def get_access_token(self) -> bool:
        """
        獲取 Access Token
        使用 apikey_dma_login 方式
        """
        try:
            from fubon_neo.sdk import FubonSDK
            
            log("使用 SDK 獲取 Access Token...")
            sdk = FubonSDK()
            
            # 使用 API Key DMA 登入獲取 token
            # 注意：這需要正確配置
            log("✅ SDK 初始化完成")
            
            # 富邦 Web API 需要透過 SDK 的 exchange_realtime_token 獲取
            # 或者使用 apikey_dma_login 後獲取 session token
            
            return True
            
        except Exception as e:
            log(f"❌ 獲取 Token 失敗：{e}")
            return False
    
    def get_historical_candles(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str,
        timeframe: str = "1D"
    ) -> Optional[List[Dict]]:
        """
        獲取歷史K線數據（Web API）
        
        注意：這需要正確的 API Key 和權限
        """
        if not self.load_api_key():
            return None
        
        try:
            url = f"{self.BASE_URL}/historical/candles/{symbol}"
            headers = {
                "Content-Type": "application/json",
                "X-API-KEY": self.api_key
            }
            params = {
                "startDate": start_date,
                "endDate": end_date,
                "timeframe": timeframe
            }
            
            log(f"獲取 {symbol} 歷史K線 ({start_date} ~ {end_date})...")
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            log(f"API 回應狀態：{response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                log(f"✅ 成功獲取數據")
                return data
            else:
                log(f"❌ API 錯誤：{response.status_code}")
                log(f"回應內容：{response.text[:200]}")
                return None
                
        except Exception as e:
            log(f"❌ 請求錯誤：{e}")
            return None
    
    def get_intraday_quote(self, symbol: str) -> Optional[Dict]:
        """
        獲取即時行情（Web API）
        """
        if not self.load_api_key():
            return None
        
        try:
            url = f"{self.BASE_URL}/intraday/quote/{symbol}"
            headers = {
                "Content-Type": "application/json",
                "X-API-KEY": self.api_key
            }
            
            log(f"獲取 {symbol} 即時行情...")
            
            response = requests.get(url, headers=headers, timeout=10)
            
            log(f"API 回應狀態：{response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                log(f"✅ 成功獲取行情")
                return data
            else:
                log(f"❌ API 錯誤：{response.status_code}")
                log(f"回應內容：{response.text[:200]}")
                return None
                
        except Exception as e:
            log(f"❌ 請求錯誤：{e}")
            return None


def main():
    """主程式"""
    if len(sys.argv) < 2:
        print("""
富邦證券歷史K線工具（Web API）

使用方法：
    python3 fubon_historical_kline.py quote <股票代號>     # 即時行情
    python3 fubon_historical_kline.py candles <股票代號>   # 歷史K線

範例：
    python3 fubon_historical_kline.py quote 00887
    python3 fubon_historical_kline.py candles 00655L
""")
        return 1
    
    command = sys.argv[1].lower()
    
    if len(sys.argv) < 3:
        log("❌ 請指定股票代號")
        return 1
    
    symbol = sys.argv[2]
    
    client = FubonHistoricalData()
    
    if command == "quote":
        data = client.get_intraday_quote(symbol)
        if data:
            print(json.dumps(data, ensure_ascii=False, indent=2))
    
    elif command == "candles":
        # 計算日期範圍（最近20個交易日）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        data = client.get_historical_candles(
            symbol,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        if data:
            print(json.dumps(data, ensure_ascii=False, indent=2))
    
    else:
        log(f"❌ 未知命令：{command}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
