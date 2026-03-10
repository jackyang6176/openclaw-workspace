#!/usr/bin/env python3
"""
富邦證券K線數據獲取工具
使用富邦SDK的 marketdata.rest_client.stock.historical.candles()
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

class FubonKlineSDK:
    """富邦K線數據客戶端（使用SDK）"""
    
    def __init__(self):
        self.sdk = None
        self.accounts = None
        self.is_logged_in = False
        self.config = {}
        self.reststock = None
        
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
        
        required = ['ACCOUNT', 'ACCT_PASSWORD', 'CERT_PATH', 'CERT_PASSWORD']
        for key in required:
            if key not in self.config:
                log(f"❌ 缺少配置：{key}")
                return False
        return True
    
    def login(self) -> bool:
        """登入並建立行情連線"""
        if not self.load_env():
            return False
        
        try:
            from fubon_neo.sdk import FubonSDK
            
            log("初始化 SDK...")
            self.sdk = FubonSDK()
            
            log("執行登入...")
            result = self.sdk.login(
                self.config['ACCOUNT'],
                self.config['ACCT_PASSWORD'],
                self.config['CERT_PATH'],
                self.config['CERT_PASSWORD']
            )
            
            if result.is_success:
                self.is_logged_in = True
                self.accounts = result.data
                log("✅ 登入成功")
                
                # 建立行情連線
                log("建立行情連線...")
                self.sdk.init_realtime()
                
                # 獲取 REST client
                self.reststock = self.sdk.marketdata.rest_client.stock
                log("✅ 行情連線建立成功")
                
                return True
            else:
                log(f"❌ 登入失敗：{result.message}")
                return False
                
        except Exception as e:
            log(f"❌ 登入錯誤：{e}")
            import traceback
            log(traceback.format_exc())
            return False
    
    def get_historical_candles(
        self, 
        symbol: str, 
        from_date: str, 
        to_date: str,
        timeframe: str = "D"
    ) -> Optional[List[Dict]]:
        """
        獲取歷史K線數據
        
        Args:
            symbol: 股票代號
            from_date: 開始日期 (YYYY-MM-DD)
            to_date: 結束日期 (YYYY-MM-DD)
            timeframe: K線週期 (D=日K, W=週K, M=月K, 1=1分K, 5=5分K, etc.)
        """
        if not self.is_logged_in or not self.reststock:
            log("❌ 請先登入")
            return None
        
        try:
            log(f"獲取 {symbol} 歷史K線 ({from_date} ~ {to_date}, timeframe={timeframe})...")
            
            # 使用 SDK 的 historical.candles
            from fubon_neo.fugle_marketdata.rest.base_rest import FugleAPIError
            
            try:
                response = self.reststock.historical.candles(**{
                    "symbol": symbol,
                    "from": from_date,
                    "to": to_date,
                    "timeframe": timeframe
                })
                
                log(f"✅ 成功獲取數據")
                
                # 解析回應
                if hasattr(response, 'data'):
                    return response.data
                elif isinstance(response, dict) and 'data' in response:
                    return response['data']
                else:
                    return response
                    
            except FugleAPIError as e:
                log(f"❌ API 錯誤：{e}")
                log(f"Status Code: {e.status_code}")
                log(f"Response: {e.response_text}")
                return None
                
        except Exception as e:
            log(f"❌ 獲取數據錯誤：{e}")
            import traceback
            log(traceback.format_exc())
            return None
    
    def get_intraday_candles(self, symbol: str, timeframe: str = "5") -> Optional[List[Dict]]:
        """
        獲取盤中K線數據
        
        Args:
            symbol: 股票代號
            timeframe: K線週期 (1=1分K, 5=5分K, 10=10分K, 15=15分K, 30=30分K, 60=60分K)
        """
        if not self.is_logged_in or not self.reststock:
            log("❌ 請先登入")
            return None
        
        try:
            log(f"獲取 {symbol} 盤中K線 (timeframe={timeframe}分)...")
            
            from fubon_neo.fugle_marketdata.rest.base_rest import FugleAPIError
            
            try:
                response = self.reststock.intraday.candles(**{
                    "symbol": symbol,
                    "timeframe": timeframe
                })
                
                log(f"✅ 成功獲取數據")
                
                if hasattr(response, 'data'):
                    return response.data
                elif isinstance(response, dict) and 'data' in response:
                    return response['data']
                else:
                    return response
                    
            except FugleAPIError as e:
                log(f"❌ API 錯誤：{e}")
                return None
                
        except Exception as e:
            log(f"❌ 獲取數據錯誤：{e}")
            import traceback
            log(traceback.format_exc())
            return None
    
    def format_kline_table(self, symbol: str, data: List[Dict]) -> str:
        """格式化K線數據為表格"""
        if not data:
            return "無數據"
        
        lines = []
        lines.append("\n" + "=" * 110)
        lines.append(f"{symbol} - 最近{len(data)}個交易日K線（富邦SDK）")
        lines.append("=" * 110)
        lines.append(f"{'日期':<12} {'開盤':>10} {'最高':>10} {'最低':>10} {'收盤':>10} {'漲跌':>15} {'成交量':>20}")
        lines.append("-" * 110)
        
        prev_close = None
        for item in data:
            date = item.get('date', 'N/A')
            open_p = item.get('open', 0)
            high = item.get('high', 0)
            low = item.get('low', 0)
            close = item.get('close', 0)
            volume = item.get('volume', 0)
            change = item.get('change', 0)
            
            # 計算漲跌
            if change != 0:
                change_str = f"{change:+.2f}"
            elif prev_close is not None:
                change_val = close - prev_close
                change_pct = (change_val / prev_close) * 100 if prev_close > 0 else 0
                change_str = f"{change_val:+.2f} ({change_pct:+.2f}%)"
            else:
                change_str = "-"
            
            lines.append(f"{date:<12} {open_p:>10.2f} {high:>10.2f} {low:>10.2f} {close:>10.2f} {change_str:>20} {volume:>20,}")
            
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
        
        return "\n".join(lines)
    
    def logout(self):
        """登出"""
        if self.sdk and self.is_logged_in:
            try:
                self.sdk.logout()
                log("✅ 已登出")
            except:
                pass


def main():
    """主程式"""
    if len(sys.argv) < 2:
        symbol = "00887"
        days = 20
    else:
        symbol = sys.argv[1]
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    
    # 計算日期範圍
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days * 2)  # 乘以2確保獲取足夠交易日
    
    log(f"查詢 {symbol} 最近 {days} 個交易日K線數據（使用富邦SDK）...")
    
    client = FubonKlineSDK()
    
    if not client.login():
        log("❌ 登入失敗")
        return 1
    
    try:
        # 獲取歷史K線
        data = client.get_historical_candles(
            symbol,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            timeframe="D"  # 日K
        )
        
        if data:
            # 只取最近 days 筆
            if isinstance(data, list) and len(data) > days:
                data = data[-days:]
            
            print(client.format_kline_table(symbol, data))
        else:
            log("❌ 無法獲取數據")
            return 1
            
    finally:
        client.logout()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
