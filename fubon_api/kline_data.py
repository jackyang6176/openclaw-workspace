#!/usr/bin/env python3
"""
富邦證券 K線數據獲取工具
使用 SDK 獲取歷史行情數據
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

class FubonKlineData:
    """富邦K線數據客戶端"""
    
    def __init__(self):
        self.sdk = None
        self.accounts = None
        self.is_logged_in = False
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
        
        required = ['ACCOUNT', 'ACCT_PASSWORD', 'CERT_PATH', 'CERT_PASSWORD']
        for key in required:
            if key not in self.config:
                log(f"❌ 缺少配置：{key}")
                return False
        return True
    
    def login(self) -> bool:
        """登入"""
        if not self.load_env():
            return False
        
        try:
            from fubon_neo.sdk import FubonSDK
            self.sdk = FubonSDK()
            
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
                return True
            else:
                log(f"❌ 登入失敗：{result.message}")
                return False
                
        except Exception as e:
            log(f"❌ 登入錯誤：{e}")
            return False
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """獲取即時行情"""
        if not self.is_logged_in:
            log("❌ 請先登入")
            return None
        
        try:
            result = self.sdk.stock.query_symbol_quote(self.accounts[0], symbol)
            if result.is_success:
                return result.data
            else:
                log(f"❌ 查詢失敗：{result.message}")
                return None
        except Exception as e:
            log(f"❌ 查詢錯誤：{e}")
            return None
    
    def format_quote(self, data) -> str:
        """格式化行情數據"""
        if not data:
            return "無數據"
        
        def fmt(val):
            return f"{val:.2f}" if val is not None else "N/A"
        
        lines = []
        lines.append(f"股票：{data.symbol}")
        lines.append(f"市場：{data.market}")
        lines.append(f"參考價：{fmt(data.reference_price)}")
        lines.append(f"開盤：{fmt(data.open_price)}")
        lines.append(f"最高：{fmt(data.high_price)}")
        lines.append(f"最低：{fmt(data.low_price)}")
        lines.append(f"最新：{fmt(data.last_price)}")
        
        if data.last_price is not None and data.reference_price is not None:
            change = data.last_price - data.reference_price
            change_pct = (change / data.reference_price) * 100 if data.reference_price > 0 else 0
            lines.append(f"漲跌：{change:.2f} ({change_pct:.2f}%)")
        
        lines.append(f"買價：{fmt(data.bid_price)} ({data.bid_volume})")
        lines.append(f"賣價：{fmt(data.ask_price)} ({data.ask_volume})")
        lines.append(f"成交量：{data.total_volume:,}" if data.total_volume is not None else "成交量：N/A")
        
        return "\n".join(lines)
    
    def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """獲取多檔股票行情"""
        results = {}
        for symbol in symbols:
            data = self.get_quote(symbol)
            if data:
                results[symbol] = data
        return results
    
    def display_watchlist(self, symbols: List[str]):
        """顯示自選股行情"""
        log(f"獲取 {len(symbols)} 檔股票行情...")
        
        quotes = self.get_multiple_quotes(symbols)
        
        if not quotes:
            log("❌ 無法獲取行情")
            return
        
        print("\n" + "=" * 100)
        print(f"{'代號':<10} {'名稱':<15} {'最新價':>10} {'漲跌':>10} {'漲跌幅':>10} {'成交量':>12}")
        print("-" * 100)
        
        for symbol, data in quotes.items():
            if not data or data.last_price is None or data.reference_price is None:
                continue
            
            change = data.last_price - data.reference_price
            change_pct = (change / data.reference_price) * 100 if data.reference_price > 0 else 0
            
            # 簡化名稱顯示
            name_map = {
                '00655L': '國泰A50正2',
                '00882': '中信中國高股息',
                '00887': '永豐中國科技50'
            }
            name = name_map.get(symbol, symbol)
            
            print(f"{symbol:<10} {name:<15} {data.last_price:>10.2f} {change:>+10.2f} {change_pct:>+9.2f}% {data.total_volume:>12,}")
        
        print("=" * 100)
    
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
        print("""
富邦證券 K線/行情數據工具

使用方法：
    python3 kline_data.py quote <股票代號>           # 單檔行情
    python3 kline_data.py watch                      # 自選股行情
    python3 kline_data.py watchlist 00655L 00882     # 多檔行情

範例：
    python3 kline_data.py quote 00655L
    python3 kline_data.py watch
    python3 kline_data.py watchlist 00655L 00882 00887
""")
        return 1
    
    command = sys.argv[1].lower()
    
    client = FubonKlineData()
    
    if command == "quote":
        if len(sys.argv) < 3:
            log("❌ 請指定股票代號")
            return 1
        symbol = sys.argv[2]
        
        if client.login():
            data = client.get_quote(symbol)
            if data:
                print(client.format_quote(data))
            client.logout()
    
    elif command == "watch":
        # 預設自選股
        watchlist = ['00655L', '00882', '00887']
        
        if client.login():
            client.display_watchlist(watchlist)
            client.logout()
    
    elif command == "watchlist":
        if len(sys.argv) < 3:
            log("❌ 請指定至少一個股票代號")
            return 1
        
        symbols = sys.argv[2:]
        
        if client.login():
            client.display_watchlist(symbols)
            client.logout()
    
    else:
        log(f"❌ 未知命令：{command}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
