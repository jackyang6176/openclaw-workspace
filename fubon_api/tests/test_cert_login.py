#!/usr/bin/env python3
"""
富邦 Neo API - 憑證登入測試
使用 sdk.login(user_id, password, cert_path, cert_pass) 方法
"""
import os
import sys
import json
from datetime import datetime

# 設定日誌目錄
LOG_DIR = "/home/admin/.openclaw/workspace/fubon_api/logs"
os.makedirs(LOG_DIR, exist_ok=True)

def log_message(message, level="INFO"):
    """記錄訊息到控制台和日誌檔案"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] [{level}] {message}"
    print(log_line)
    
    # 寫入日誌檔案
    log_file = os.path.join(LOG_DIR, f"cert_login_test_{datetime.now().strftime('%Y%m%d')}.log")
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')

def test_cert_login():
    """測試憑證登入"""
    print("=" * 70)
    print("富邦 Neo API - 憑證登入測試")
    print("=" * 70)
    print(f"測試時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 從 .env 檔案讀取配置
    env_path = "/home/admin/.env/fubon.env"
    config = {}
    
    if os.path.exists(env_path):
        log_message(f"讀取環境變數檔案：{env_path}")
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        config[key] = value
            log_message("✅ 環境變數讀取成功")
        except Exception as e:
            log_message(f"❌ 讀取環境變數失敗：{e}", "ERROR")
            return False
    else:
        log_message(f"環境變數檔案不存在：{env_path}", "ERROR")
        return False
    
    user_id = config.get('ACCOUNT')
    password = config.get('ACCT_PASSWORD')
    cert_path = config.get('CERT_PATH')
    cert_password = config.get('CERT_PASSWORD')
    
    # 驗證必要參數
    if not all([user_id, password, cert_path, cert_password]):
        log_message("缺少必要的登入參數", "ERROR")
        return False
    
    # 檢查憑證檔案是否存在
    if not os.path.exists(cert_path):
        log_message(f"憑證檔案不存在：{cert_path}", "ERROR")
        return False
    
    log_message(f"用戶 ID：{user_id}")
    log_message(f"密碼：{'*' * len(password)}")
    log_message(f"憑證路徑：{cert_path}")
    log_message(f"憑證檔案大小：{os.path.getsize(cert_path)} bytes")
    log_message(f"憑證密碼：{'*' * len(cert_password)}")
    print()
    
    # 導入 SDK
    log_message("正在導入富邦 SDK...")
    try:
        from fubon_neo.sdk import FubonSDK
        import fubon_neo
        log_message(f"✅ SDK 導入成功，版本：{fubon_neo.__version__}")
        print()
    except Exception as e:
        log_message(f"❌ SDK 導入失敗：{e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False
    
    # 初始化 SDK
    log_message("初始化 FubonSDK...")
    try:
        sdk = FubonSDK()
        log_message("✅ SDK 初始化成功")
        print()
    except Exception as e:
        log_message(f"❌ SDK 初始化失敗：{e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False
    
    # 使用憑證登入
    log_message("=" * 70)
    log_message("執行 sdk.login(user_id, password, cert_path, cert_password)...")
    log_message("=" * 70)
    
    try:
        # 使用憑證登入
        result = sdk.login(user_id, password, cert_path, cert_password)
        
        log_message(f"登入結果類型：{type(result)}")
        log_message(f"登入結果：{result}")
        
        # 檢查登入結果
        if hasattr(result, 'is_success'):
            log_message(f"is_success：{result.is_success}")
        
        if hasattr(result, 'data'):
            log_message(f"data：{result.data}")
        
        if hasattr(result, 'message'):
            log_message(f"message：{result.message}")
        
        # 判斷登入是否成功
        if hasattr(result, 'is_success') and result.is_success:
            log_message("✅ 憑證登入成功！")
            
            # 顯示帳戶資訊
            if hasattr(result, 'data') and result.data:
                print()
                log_message("帳戶資訊：")
                for i, account in enumerate(result.data):
                    log_message(f"  帳戶 {i+1}：{account}")
            
            # 測試初始化行情連線
            print()
            log_message("測試初始化行情連線...")
            try:
                sdk.init_realtime()
                log_message("✅ 行情連線初始化成功")
            except Exception as e:
                log_message(f"⚠️ 行情連線初始化失敗：{e}", "WARNING")
            
            return True
        else:
            log_message("❌ 憑證登入失敗", "ERROR")
            if hasattr(result, 'message') and result.message:
                log_message(f"錯誤訊息：{result.message}", "ERROR")
            return False
            
    except Exception as e:
        log_message(f"❌ 登入過程發生錯誤：{e}", "ERROR")
        import traceback
        traceback.print_exc()
        
        # 記錄詳細錯誤到日誌
        error_log = os.path.join(LOG_DIR, f"cert_login_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        with open(error_log, 'w', encoding='utf-8') as f:
            f.write(f"登入錯誤時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"錯誤訊息：{e}\n")
            f.write("\n完整堆疊追蹤：\n")
            traceback.print_exc(file=f)
        
        log_message(f"詳細錯誤已記錄至：{error_log}", "ERROR")
        return False

def main():
    """主程式"""
    success = test_cert_login()
    
    print()
    print("=" * 70)
    if success:
        print("✅ 測試完成：憑證登入成功")
    else:
        print("❌ 測試完成：憑證登入失敗")
    print("=" * 70)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
