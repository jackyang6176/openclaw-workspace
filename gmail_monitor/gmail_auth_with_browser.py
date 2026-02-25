#!/usr/bin/env python3
"""
Gmail 認證腳本 - 使用 OpenClaw Browser 工具處理 OAuth
"""

import os
import json
import pickle
import webbrowser
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API 權限範圍
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail_with_browser():
    """使用瀏覽器進行 Gmail OAuth 認證"""
    creds = None
    token_path = '/home/admin/.openclaw/workspace/gmail_monitor/token.pickle'
    credentials_path = '/home/admin/.openclaw/workspace/gmail_monitor/credentials.json'
    
    # 檢查是否有現有的 token
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    # 如果沒有有效憑證，進行 OAuth 流程
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # 使用 OpenClaw browser 工具
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            
            print("📧 正在啟動瀏覽器進行 Gmail 認證...")
            print("請在瀏覽器中完成授權流程")
            
            # 嘗試使用系統瀏覽器
            try:
                # 設定瀏覽器路徑
                webbrowser.register('chrome', None, 
                                  webbrowser.BackgroundBrowser('/usr/bin/google-chrome-stable'))
                
                # 啟動 OAuth 伺服器並打開瀏覽器
                creds = flow.run_local_server(
                    port=8080,
                    authorization_prompt_message='請在瀏覽器中完成授權',
                    success_message='授權成功！您可以關閉瀏覽器。',
                    open_browser=True
                )
            except Exception as e:
                print(f"使用網路瀏覽器失敗: {e}")
                print("請手動訪問授權 URL 並輸入授權碼")
                creds = flow.run_console()
        
        # 保存憑證
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('gmail', 'v1', credentials=creds)

def test_gmail_connection():
    """測試 Gmail 連接"""
    try:
        service = authenticate_gmail_with_browser()
        # 測試獲取郵件列表
        results = service.users().messages().list(userId='me', maxResults=5).execute()
        messages = results.get('messages', [])
        
        print("✅ Gmail 連接成功！")
        print(f"📬 找到 {len(messages)} 封郵件")
        
        if messages:
            # 獲取第一封郵件的詳細資訊
            msg = service.users().messages().get(userId='me', id=messages[0]['id']).execute()
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '無主題')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '未知寄件人')
            print(f"📨 最新郵件: {subject} (來自: {sender})")
        
        return True
    except Exception as e:
        print(f"❌ Gmail 連接失敗: {e}")
        return False

if __name__ == '__main__':
    print("📧 Gmail 認證測試")
    test_gmail_connection()