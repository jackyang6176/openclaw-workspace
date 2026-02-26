#!/usr/bin/env python3
"""
富邦 Neo API 連線測試腳本
"""
import os
import json
from datetime import datetime

# 導入富邦 SDK
from fubon_neo.sdk import FubonSDK

def test_sdk_import():
    """測試 SDK 導入"""
    print("=" * 60)
    print("富邦 Neo API 連線測試")
    print("=" * 60)
    print(f"測試時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 測試 SDK 導入
    try:
        from fubon_neo.sdk import FubonSDK
        import fubon_neo
        print(f"✅ SDK 導入成功")
        print(f"   版本：{fubon_neo.__version__}")
        return True
    except Exception as e:
        print(f"❌ SDK 導入失敗：{e}")
        return False

def test_config_file():
    """測試配置文件"""
    config_path = "/home/admin/.openclaw/workspace/fubon_api/config/credentials.json"
    
    if os.path.exists(config_path):
        print(f"✅ 配置文件存在：{config_path}")
        return True
    else:
        print(f"⚠️  配置文件不存在：{config_path}")
        print(f"   請在配置文件中填入以下資訊：")
        print(f"""
{{
    "user_id": "您的身分證字號",
    "password": "您的電子平台密碼",
    "cert_path": "網頁憑證路徑（可選）",
    "cert_password": "憑證密碼（可選）",
    "api_key": "API Key（可選，v2.2.7+）"
}}
        """)
        return False

def test_login():
    """測試登入（需要配置文件）"""
    config_path = "/home/admin/.openclaw/workspace/fubon_api/config/credentials.json"
    
    if not os.path.exists(config_path):
        print(f"⚠️  跳過登入測試（配置文件不存在）")
        return None
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        sdk = FubonSDK()
        
        # 嘗試登入
        if 'cert_path' in config and config['cert_path']:
            # 使用網頁憑證登入
            accounts = sdk.login(
                config['user_id'],
                config['password'],
                config['cert_path'],
                config.get('cert_password', '')
            )
        elif 'api_key' in config and config['api_key']:
            # 使用 API Key 登入
            accounts = sdk.login_with_api_key(
                config['user_id'],
                config['api_key']
            )
        else:
            print(f"⚠️  未找到認證資訊")
            return None
        
        print(f"✅ 登入成功")
        print(f"   帳號：{accounts.data[0].get('user_id', 'N/A')}")
        
        # 測試建立行情連線
        sdk.init_realtime()
        print(f"✅ 行情連線建立成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 登入失敗：{e}")
        return False

def test_market_data():
    """測試行情數據（需要登入）"""
    print()
    print("測試標的：")
    print("  - 00655L 國泰 A50 正 2")
    print("  - 00882 中信中國高股息")
    print("  - 00887 永豐中國科技 50 大")
    print()
    
    # 這裡需要登入後才能測試
    print("⚠️  需要登入後才能測試行情數據")
    return None

def main():
    """主測試流程"""
    results = {}
    
    # 測試 1：SDK 導入
    results['sdk_import'] = test_sdk_import()
    print()
    
    # 測試 2：配置文件
    results['config'] = test_config_file()
    print()
    
    # 測試 3：登入
    results['login'] = test_login()
    print()
    
    # 測試 4：行情數據
    results['market_data'] = test_market_data()
    print()
    
    # 總結
    print("=" * 60)
    print("測試總結")
    print("=" * 60)
    print(f"SDK 導入：{'✅ 成功' if results['sdk_import'] else '❌ 失敗'}")
    print(f"配置文件：{'✅ 存在' if results['config'] else '⚠️  不存在'}")
    print(f"登入測試：{ '✅ 成功' if results['login'] else ('❌ 失敗' if results['login'] is False else '⏸️  跳過')}")
    print(f"行情測試：{ '✅ 成功' if results['market_data'] else ('❌ 失敗' if results['market_data'] is False else '⏸️  跳過')}")
    print()
    
    if results['sdk_import'] and results['config']:
        print("✅ 環境準備完成！")
        print()
        print("下一步：")
        print("  1. 填寫配置文件 /home/admin/.openclaw/workspace/fubon_api/config/credentials.json")
        print("  2. 重新執行測試腳本驗證登入")
        print("  3. 登入成功後獲取持倉數據")
    else:
        print("⚠️  環境準備未完成，請檢查上述錯誤")

if __name__ == "__main__":
    main()
