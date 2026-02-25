#!/usr/bin/env python3
"""
Gmail 監控調試腳本 - 簡化版本
"""

import pickle
import os
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def test_gmail_connection():
    """測試 Gmail 連接"""
    print("1. 檢查 token.pickle...")
    if not os.path.exists('token.pickle'):
        print("❌ token.pickle 不存在")
        return False
    
    print("2. 載入 token...")
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    
    print(f"3. Token 有效狀態: {creds.valid}")
    print(f"4. Token 過期狀態: {creds.expired}")
    
    # 刷新 token（如果需要）
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("5. 嘗試刷新 token...")
            try:
                creds.refresh(Request())
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
                print("✅ Token 刷新成功")
            except Exception as e:
                print(f"❌ Token 刷新失敗: {e}")
                return False
        else:
            print("❌ token 無效且無法刷新")
            return False
    
    print("6. 建立 Gmail 服務...")
    try:
        service = build('gmail', 'v1', credentials=creds)
        print("✅ Gmail 服務建立成功")
    except Exception as e:
        print(f"❌ Gmail 服務建立失敗: {e}")
        return False
    
    print("7. 測試獲取郵件列表...")
    try:
        results = service.users().messages().list(userId='me', maxResults=1).execute()
        messages = results.get('messages', [])
        print(f"✅ 成功獲取郵件列表，找到 {len(messages)} 封郵件")
        return True
    except Exception as e:
        print(f"❌ 獲取郵件列表失敗: {e}")
        return False

if __name__ == "__main__":
    print("開始 Gmail 連接測試...")
    success = test_gmail_connection()
    if success:
        print("\n✅ Gmail 連接測試成功！")
    else:
        print("\n❌ Gmail 連接測試失敗！")