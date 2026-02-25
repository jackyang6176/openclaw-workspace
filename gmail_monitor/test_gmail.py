#!/usr/bin/env python3
"""
Gmail 監控測試腳本 - 簡化版本
"""

import pickle
import os
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def test_gmail_connection():
    """測試 Gmail 連接"""
    print("正在測試 Gmail 連接...")
    
    # 載入 token
    if not os.path.exists('token.pickle'):
        print("❌ token.pickle 不存在")
        return False
    
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    
    # 刷新 token（如果需要）
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("正在刷新 token...")
            creds.refresh(Request())
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        else:
            print("❌ token 無效且無法刷新")
            return False
    
    # 建立 Gmail 服務
    print("正在建立 Gmail 服務...")
    service = build('gmail', 'v1', credentials=creds)
    
    # 測試基本查詢
    print("正在測試基本查詢...")
    results = service.users().messages().list(userId='me', maxResults=1).execute()
    messages = results.get('messages', [])
    
    if messages:
        print(f"✅ 成功連接到 Gmail，找到 {len(messages)} 封郵件")
        return True
    else:
        print("✅ 成功連接到 Gmail，但沒有找到郵件")
        return True

if __name__ == "__main__":
    success = test_gmail_connection()
    if success:
        print("\nGmail 連接測試成功！")
    else:
        print("\nGmail 連接測試失敗！")