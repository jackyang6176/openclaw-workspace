#!/usr/bin/env python3
"""
Gmail 認證腳本 - 最終版本
使用手動授權碼完成認證
"""

import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API 權限範圍
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_with_auth_code(auth_code):
    """使用授權碼完成認證"""
    creds = None
    
    # 讀取 credentials.json
    if os.path.exists('credentials.json'):
        # 建立 flow
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        
        # 使用授權碼完成認證
        flow.fetch_token(code=auth_code)
        creds = flow.credentials
        
        # 保存 token
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
        
        print("✅ Gmail 認證成功！")
        print("✅ token.pickle 已生成")
        return True
    else:
        print("❌ 找不到 credentials.json")
        return False

def test_gmail_connection():
    """測試 Gmail 連接"""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("❌ 憑證無效")
            return False
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        # 測試獲取郵件列表
        results = service.users().messages().list(userId='me', maxResults=1).execute()
        print("✅ Gmail 連接測試成功！")
        return True
    except Exception as e:
        print(f"❌ Gmail 連接失敗: {e}")
        return False

if __name__ == '__main__':
    print("📧 Gmail 認證系統啟動...")
    
    # 讀取授權碼
    if os.path.exists('auth_code.txt'):
        with open('auth_code.txt', 'r') as f:
            auth_code = f.read().strip()
        
        print(f"使用網路授權碼: {auth_code[:20]}...")
        
        # 完成認證
        if authenticate_with_auth_code(auth_code):
            # 測試連接
            test_gmail_connection()
        else:
            print("❌ 認證失敗")
    else:
        print("❌ 找不到 auth_code.txt")