#!/usr/bin/env python3
"""
Gmail 監控簡化版本 - 僅測試基本功能
"""

import pickle
import os
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def test_basic_gmail_access():
    """測試基本 Gmail 訪問"""
    print("正在測試基本 Gmail 訪問...")
    
    # 載入 token
    if not os.path.exists('token.pickle'):
        print("❌ token.pickle 不存在")
        return False
    
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    
    # 刷新 token（如果需要）
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        else:
            print("❌ token 無效且無法刷新")
            return False
    
    # 建立 Gmail 服務
    service = build('gmail', 'v1', credentials=creds)
    
    # 測試獲取郵箱概要
    try:
        profile = service.users().getProfile(userId='me').execute()
        print(f"✅ 成功連接到 Gmail 帳戶: {profile.get('emailAddress', '未知')}")
        
        # 測試獲取未讀郵件數量
        results = service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=1
        ).execute()
        
        total_unread = results.get('resultSizeEstimate', 0)
        print(f"📬 未讀郵件總數: {total_unread}")
        
        return True
        
    except Exception as e:
        print(f"❌ Gmail 訪問失敗: {e}")
        return False

if __name__ == "__main__":
    success = test_basic_gmail_access()
    if success:
        print("\n✅ 基本 Gmail 訪問測試通過！")
    else:
        print("\n❌ 基本 Gmail 訪問測試失敗！")