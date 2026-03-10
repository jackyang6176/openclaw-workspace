#!/usr/bin/env python3
"""
富邦證券快速交易工具
直接呼叫 API，無需經過大模型

使用方法：
    python3 quick_trade.py login              # 登入測試
    python3 quick_trade.py balance            # 查詢餘額
    python3 quick_trade.py positions          # 查詢持倉
    python3 quick_trade.py quote 00655L       # 查詢行情
    python3 quick_trade.py quote 00882        # 查詢行情
    python3 quick_trade.py buy 00655L 1000    # 買入股票（張數）
    python3 quick_trade.py sell 00655L 1000   # 賣出股票（張數）
"""
import os
import sys
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

# 設定日誌
LOG_DIR = "/home/admin/.openclaw/workspace/fubon_api/logs"
os.makedirs(LOG_DIR, exist_ok=True)

def log(message: str):
    """簡易日誌"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

class FubonTrader:
    """富邦證券交易客戶端"""
    
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
                
                if self.accounts:
                    account = self.accounts[0]
                    log(f"   帳戶：{account.name}")
                    log(f"   分公司：{account.branch_no}")
                    log(f"   帳號：{account.account}")
                
                self.sdk.init_realtime()
                return True
            else:
                log(f"❌ 登入失敗：{result.message}")
                return False
                
        except Exception as e:
            log(f"❌ 登入錯誤：{e}")
            return False
    
    def get_balance(self):
        """查詢餘額"""
        if not self.is_logged_in:
            log("❌ 請先登入")
            return
        
        try:
            result = self.sdk.accounting.bank_remain(self.accounts[0])
            if result.is_success:
                data = result.data
                log("✅ 餘額查詢成功")
                log(f"   幣別：{data.currency}")
                log(f"   總餘額：{data.balance:,.0f}")
                log(f"   可用餘額：{data.available_balance:,.0f}")
            else:
                log(f"❌ 查詢失敗：{result.message}")
        except Exception as e:
            log(f"❌ 查詢錯誤：{e}")
    
    def get_positions(self):
        """查詢持倉"""
        if not self.is_logged_in:
            log("❌ 請先登入")
            return
        
        try:
            result = self.sdk.accounting.unrealized_gains_and_loses(self.accounts[0])
            if result.is_success:
                data = result.data
                log("✅ 持倉查詢成功")
                if data:
                    for pos in data:
                        log(f"   {pos.symbol}: {pos.quantity} 股, 成本 {pos.avg_price:.2f}")
                else:
                    log("   無持倉")
            else:
                log(f"❌ 查詢失敗：{result.message}")
        except Exception as e:
            log(f"❌ 查詢錯誤：{e}")
    
    def get_quote(self, symbol: str):
        """查詢行情"""
        if not self.is_logged_in:
            log("❌ 請先登入")
            return
        
        try:
            result = self.sdk.stock.query_symbol_quote(self.accounts[0], symbol)
            if result.is_success:
                data = result.data
                log(f"✅ {symbol} 行情")
                log(f"   市場：{data.market}")
                log(f"   參考價：{data.reference_price:.2f}")
                log(f"   開盤：{data.open_price:.2f}")
                log(f"   最高：{data.high_price:.2f}")
                log(f"   最低：{data.low_price:.2f}")
                log(f"   最新：{data.last_price:.2f}")
                log(f"   買價：{data.bid_price:.2f} ({data.bid_volume})")
                log(f"   賣價：{data.ask_price:.2f} ({data.ask_volume})")
                log(f"   成交量：{data.total_volume:,}")
            else:
                log(f"❌ 查詢失敗：{result.message}")
        except Exception as e:
            log(f"❌ 查詢錯誤：{e}")
    
    def buy(self, symbol: str, quantity: int, price: float = 0):
        """
        買入股票
        quantity: 股數（1張=1000股）
        price: 0 表示市價單
        """
        if not self.is_logged_in:
            log("❌ 請先登入")
            return
        
        try:
            from fubon_neo.sdk import Order
            
            order = Order(
                buy_sell="Buy",
                symbol=symbol,
                quantity=quantity,
                price=price,
                order_type="ROD" if price > 0 else "IOC",
                price_type="Limit" if price > 0 else "Market"
            )
            
            result = self.sdk.stock.place_order(self.accounts[0], order)
            
            if result.is_success:
                log(f"✅ 買入委託成功")
                log(f"   股票：{symbol}")
                log(f"   數量：{quantity} 股")
                log(f"   價格：{price if price > 0 else '市價'}")
            else:
                log(f"❌ 委託失敗：{result.message}")
                
        except Exception as e:
            log(f"❌ 下單錯誤：{e}")
    
    def sell(self, symbol: str, quantity: int, price: float = 0):
        """
        賣出股票
        quantity: 股數（1張=1000股）
        price: 0 表示市價單
        """
        if not self.is_logged_in:
            log("❌ 請先登入")
            return
        
        try:
            from fubon_neo.sdk import Order
            
            order = Order(
                buy_sell="Sell",
                symbol=symbol,
                quantity=quantity,
                price=price,
                order_type="ROD" if price > 0 else "IOC",
                price_type="Limit" if price > 0 else "Market"
            )
            
            result = self.sdk.stock.place_order(self.accounts[0], order)
            
            if result.is_success:
                log(f"✅ 賣出委託成功")
                log(f"   股票：{symbol}")
                log(f"   數量：{quantity} 股")
                log(f"   價格：{price if price > 0 else '市價'}")
            else:
                log(f"❌ 委託失敗：{result.message}")
                
        except Exception as e:
            log(f"❌ 下單錯誤：{e}")
    
    def logout(self):
        """登出"""
        if self.sdk and self.is_logged_in:
            try:
                self.sdk.logout()
                log("✅ 已登出")
            except:
                pass


def show_usage():
    """顯示使用說明"""
    print("""
富邦證券快速交易工具

使用方法：
    python3 quick_trade.py login                    # 登入測試
    python3 quick_trade.py balance                  # 查詢餘額
    python3 quick_trade.py positions                # 查詢持倉
    python3 quick_trade.py quote <股票代號>          # 查詢行情
    python3 quick_trade.py buy <股票代號> <數量> [價格]   # 買入
    python3 quick_trade.py sell <股票代號> <數量> [價格]  # 賣出

範例：
    python3 quick_trade.py quote 00655L
    python3 quick_trade.py buy 00655L 1000          # 買入 1 張市價單
    python3 quick_trade.py buy 00655L 1000 30.5     # 買入 1 張限價 30.5
    python3 quick_trade.py sell 00655L 1000         # 賣出 1 張市價單
""")


def main():
    """主程式"""
    if len(sys.argv) < 2:
        show_usage()
        return 1
    
    command = sys.argv[1].lower()
    trader = FubonTrader()
    
    if command == "login":
        trader.login()
        trader.logout()
    
    elif command == "balance":
        if trader.login():
            trader.get_balance()
            trader.logout()
    
    elif command == "positions":
        if trader.login():
            trader.get_positions()
            trader.logout()
    
    elif command == "quote":
        if len(sys.argv) < 3:
            log("❌ 請指定股票代號")
            return 1
        symbol = sys.argv[2]
        if trader.login():
            trader.get_quote(symbol)
            trader.logout()
    
    elif command == "buy":
        if len(sys.argv) < 4:
            log("❌ 請指定股票代號和數量")
            return 1
        symbol = sys.argv[2]
        quantity = int(sys.argv[3])
        price = float(sys.argv[4]) if len(sys.argv) > 4 else 0
        if trader.login():
            trader.buy(symbol, quantity, price)
            trader.logout()
    
    elif command == "sell":
        if len(sys.argv) < 4:
            log("❌ 請指定股票代號和數量")
            return 1
        symbol = sys.argv[2]
        quantity = int(sys.argv[3])
        price = float(sys.argv[4]) if len(sys.argv) > 4 else 0
        if trader.login():
            trader.sell(symbol, quantity, price)
            trader.logout()
    
    else:
        log(f"❌ 未知命令：{command}")
        show_usage()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
