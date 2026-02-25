#!/usr/bin/env python3
"""
簡單 Gmail 連接測試
"""

import pickle
import os
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def test_gmail_connection():
    """測試 Gmail 連接"""
    print("📧 簡單 Gmail 連接測試...")
    
    # 載入 token
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        print("✅ token.pickle 已載入")
    else:
        print("❌ token.pickle 不存在")
        return False
    
    # 檢查 token 是否有效
    if not creds or not creds.valid:
        print("❌ token 無效")
        return False
    
    try:
        # 建立 Gmail 服務
        service = build('gmail', 'v1', credentials=creds)
        print("✅ Gmail 服務已建立")
        
        # 獲取使用者資料
        profile = service.users().getProfile(userId='me').execute()
        print(f"✅ 使用者 ID: {profile['emailAddress']}")
        
        # 獲取未讀郵件數量
        results = service.users().messages().list(
            userId='me', 
            q='is:unread'
        ).execute()
        
        messages = results.get('messages', [])
        print(f"📬 未讀郵件數量: {len(messages)}")
        
        if messages:
            # 顯示最新郵件的主題
            msg = service.users().messages().get(
                userId='me', 
                id=messages[0]['id']
            ).execute()
            
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h[' value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            
            print(f"📨 最新郵件: {subject}")
            print(f"📤 寄件人: {sender}")
        
        return True
        
    except Exception as e:
        print(f"❌ Gmail API 錯誤: {str(e)}")
        return False

if __name__ == '__main__':
    test_gmail_connection()