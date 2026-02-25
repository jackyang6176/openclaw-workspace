#!/usr/bin/env python3
"""
Gmail 認證測試腳本
"""

import pickle
import os
from google.auth.transport.requests import Request

def test_auth():
    """測試 Gmail 認證"""
    print("正在測試 Gmail 認證...")
    
    # 檢查 token.pickle 是否存在
    if not os.path.exists('token.pickle'):
        print("❌ token.pickle 不存在")
        return False
    
    try:
        # 載入 token
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        
        print(f"✅ 成功載入 token")
        print(f"Token 有效: {creds.valid}")
        print(f"Token 已過期: {creds.expired if hasattr(creds, 'expired') else 'N/A'}")
        
        # 嘗試刷新 token（如果需要）
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 正在刷新 token...")
                creds.refresh(Request())
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
                print("✅ Token 刷新成功")
            else:
                print("❌ Token 無效且無法刷新")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ 認證測試失敗: {e}")
        return False

if __name__ == "__main__":
    success = test_auth()
    if success:
        print("\n✅ Gmail 認證測試通過！")
    else:
        print("\n❌ Gmail 認證測試失敗！")