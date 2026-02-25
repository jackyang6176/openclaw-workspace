#!/usr/bin/env python3
"""
Gmail 監控測試腳本
測試 Gmail API 連接和郵件監控功能
"""

import pickle
import os
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def test_gmail_connection():
    """測試 Gmail API 連接"""
    print("📧 測試 Gmail 監控系統...")
    
    # 載入 token
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        print("✅ token.pickle 已載入")
    else:
        print("❌ token.pickle 不存在")
        return False
    
    # 刷新 token（如果需要）
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 刷新 token...")
            creds.refresh(Request())
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
            print("✅ token 已刷新")
        else:
            print("❌ token 無效且無法刷新")
            return False
    
    # 建立 Gmail 服務
    try:
        service = build('gmail', 'v1', credentials=creds)
        print("✅ Gmail 服務已建立")
        
        # 測試獲取郵件列表
        results = service.users().messages().list(
            userId='me', 
            maxResults=5,
            q='is:unread'
        ).execute()
        
        messages = results.get('messages', [])
        print(f"✅ 成功獲取 Gmail 數據")
        print(f"📬 未讀郵件數量: {len(messages)}")
        
        if messages:
            # 獲取第一封郵件的詳細資訊
            msg = service.users().messages().get(
                userId='me', 
                id=messages[0]['id']
            ).execute()
            
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '無主題')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '未知寄件者')
            
            print(f"📨 最新未讀郵件:")
            print(f"   主題: {subject}")
            print(f"   寄件者: {sender}")
        
        return True
        
    except Exception as e:
        print(f"❌ Gmail API 錯誤: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_gmail_connection()
    if success:
        print("\n🎉 Gmail 監控設定正確！")
        print("✅ 系統可以正常監控您的 Gmail")
    else:
        print("\n❌ Gmail 監控設定有問題")
        print("⚠️ 請檢查授權設定")