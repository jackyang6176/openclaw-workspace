#!/usr/bin/env python3
"""
富邦證券 Neo API 整合客戶端
功能：登入、查詢持倉、查詢行情、下單
"""
import os
import sys
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

# 設定日誌目錄
LOG_DIR = "/home/admin/.openclaw/workspace/fubon_api/logs"
os.makedirs(LOG_DIR, exist_ok=True)

class FubonClient:
    """富邦證券 API 客戶端"""
    
    def __init__(self):
        self.sdk = None
        self.accounts = None
        self.is_logged_in = False
        self.env_config = {}
        
    def log(self, message: str, level: str = "INFO"):
        """記錄日誌"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] [{level}] {message}"
        print(log_line)
        
        log_file = os.path.join(LOG_DIR, f"fubon_client_{datetime.now().strftime('%Y%m%d')}.log")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
    
    def load_config(self) -> bool:
        """載入環境配置"""
        env_path = "/home/admin/.env/fubon.env"
        
        if not os.path.exists(env_path):
            self.log(f"配置檔案不存在：{env_path}", "ERROR")
            return False
        
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        self.env_config[key] = value
            
            required = ['ACCOUNT', 'ACCT_PASSWORD', 'CERT_PATH', 'CERT_PASSWORD']
            for key in required:
                if key not in self.env_config:
                    self.log(f"缺少必要配置：{key}", "ERROR")
                    return False
            
            self.log("✅ 配置載入成功")
            return True
            
        except Exception as e:
            self.log(f"載入配置失敗：{e}", "ERROR")
            return False
    
    def init_sdk(self) -> bool:
        """初始化 SDK"""
        try:
            from fubon_neo.sdk import FubonSDK
            import fubon_neo
            
            self.sdk = FubonSDK()
            self.log(f"✅ SDK 初始化成功 (版本：{fubon_neo.__version__})")
            return True
            
        except Exception as e:
            self.log(f"❌ SDK 初始化失敗：{e}", "ERROR")
            return False
    
    def login(self) -> bool:
        """登入富邦證券"""
        if not self.sdk:
            if not self.init_sdk():
                return False
        
        if not self.env_config:
            if not self.load_config():
                return False
        
        user_id = self.env_config['ACCOUNT']
        password = self.env_config['ACCT_PASSWORD']
        cert_path = self.env_config['CERT_PATH']
        cert_password = self.env_config['CERT_PASSWORD']
        
        # 檢查憑證檔案
        if not os.path.exists(cert_path):
            self.log(f"憑證檔案不存在：{cert_path}", "ERROR")
            return False
        
        self.log("=" * 70)
        self.log("執行登入...")
        self.log(f"用戶：{user_id}")
        self.log(f"憑證：{cert_path}")
        
        try:
            result = self.sdk.login(user_id, password, cert_path, cert_password)
            
            if hasattr(result, 'is_success') and result.is_success:
                self.is_logged_in = True
                self.accounts = result.data if hasattr(result, 'data') else None
                
                self.log("✅ 登入成功！")
                
                if self.accounts:
                    self.log("帳戶資訊：")
                    for i, account in enumerate(self.accounts):
                        self.log(f"  帳戶 {i+1}：{account}")
                
                # 初始化行情連線
                try:
                    self.sdk.init_realtime()
                    self.log("✅ 行情連線初始化成功")
                except Exception as e:
                    self.log(f"⚠️ 行情連線初始化失敗：{e}", "WARNING")
                
                return True
            else:
                message = result.message if hasattr(result, 'message') else "未知錯誤"
                self.log(f"❌ 登入失敗：{message}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ 登入過程發生錯誤：{e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False
    
    def get_balance(self) -> Optional[Dict]:
        """查詢帳戶餘額"""
        if not self.is_logged_in or not self.accounts:
            self.log("未登入，無法查詢餘額", "ERROR")
            return None
        
        try:
            self.log("=" * 70)
            self.log("查詢帳戶餘額...")
            
            # 使用 bank_remain 查詢銀行餘額
            account = self.accounts[0]
            result = self.sdk.accounting.bank_remain(account)
            
            self.log(f"餘額查詢結果：{result}")
            
            if hasattr(result, 'is_success') and result.is_success:
                self.log("✅ 餘額查詢成功")
                return result.data if hasattr(result, 'data') else None
            else:
                message = result.message if hasattr(result, 'message') else "未知錯誤"
                self.log(f"❌ 餘額查詢失敗：{message}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ 餘額查詢錯誤：{e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return None
    
    def get_stock_quote(self, symbol: str) -> Optional[Dict]:
        """查詢股票行情"""
        if not self.is_logged_in:
            self.log("未登入，無法查詢行情", "ERROR")
            return None
        
        try:
            self.log("=" * 70)
            self.log(f"查詢股票行情：{symbol}")
            
            # 使用 query_symbol_quote 查詢行情
            account = self.accounts[0]
            result = self.sdk.stock.query_symbol_quote(account, symbol)
            
            self.log(f"行情查詢結果：{result}")
            
            if hasattr(result, 'is_success') and result.is_success:
                self.log("✅ 行情查詢成功")
                return result.data if hasattr(result, 'data') else None
            else:
                message = result.message if hasattr(result, 'message') else "未知錯誤"
                self.log(f"❌ 行情查詢失敗：{message}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ 行情查詢錯誤：{e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return None
    
    def get_positions(self) -> Optional[List]:
        """查詢持倉（未實現損益）"""
        if not self.is_logged_in or not self.accounts:
            self.log("未登入，無法查詢持倉", "ERROR")
            return None
        
        try:
            self.log("=" * 70)
            self.log("查詢持倉（未實現損益）...")
            
            # 使用 unrealized_gains_and_loses 查詢持倉
            account = self.accounts[0]
            result = self.sdk.accounting.unrealized_gains_and_loses(account)
            
            self.log(f"持倉查詢結果：{result}")
            
            if hasattr(result, 'is_success') and result.is_success:
                self.log("✅ 持倉查詢成功")
                return result.data if hasattr(result, 'data') else None
            else:
                message = result.message if hasattr(result, 'message') else "未知錯誤"
                self.log(f"❌ 持倉查詢失敗：{message}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ 持倉查詢錯誤：{e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return None
    
    def logout(self):
        """登出"""
        if self.sdk and self.is_logged_in:
            try:
                self.sdk.logout()
                self.log("✅ 已登出")
            except:
                pass
        self.is_logged_in = False
        self.accounts = None


def main():
    """主程式 - 執行完整測試"""
    print("=" * 70)
    print("富邦證券 Neo API 整合測試")
    print("=" * 70)
    print(f"測試時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    client = FubonClient()
    
    # 1. 登入
    if not client.login():
        print("\n❌ 登入失敗，測試中止")
        return 1
    
    print()
    
    # 2. 查詢帳戶餘額
    balance = client.get_balance()
    
    print()
    
    # 3. 查詢持倉
    positions = client.get_positions()
    
    print()
    
    # 4. 查詢行情（測試股票）
    test_symbols = ['00655L', '00882', '00887']
    for symbol in test_symbols:
        quote = client.get_stock_quote(symbol)
        print()
    
    # 5. 登出
    client.logout()
    
    print("=" * 70)
    print("✅ 測試完成")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
