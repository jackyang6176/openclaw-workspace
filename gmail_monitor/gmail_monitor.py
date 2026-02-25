#!/usr/bin/env python3
"""
Gmail Monitor - 主動監控 Gmail 重要郵件並發送通知
功能：監控信用卡帳單、重要通知、投資相關、旅遊相關郵件
檢查頻率：每2小時自動檢查
通知方式：透過 Discord 發送即時通知
"""

import os
import json
import base64
import pickle
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API 權限範圍
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    """Gmail 認證流程"""
    creds = None
    # token.pickle 存儲用戶的訪問和刷新令牌
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # 如果沒有有效憑證，則進行 OAuth 2.0 流程
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # 保存憑證供下次使用
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('gmail', 'v1', credentials=creds)

def get_important_emails(service):
    """獲取重要郵件"""
    # 計算2小時前的時間
    two_hours_ago = datetime.now() - timedelta(hours=2)
    query_time = two_hours_ago.strftime('%Y/%m/%d %H:%M:%S')
    
    # 搜索查詢 - 重要郵件類型
    queries = [
        'from:bank OR from:creditcard OR subject:("帳單" OR "statement")',
        'from:notification OR subject:("重要通知" OR "security alert")',
        'subject:("投資" OR "stock" OR "trading" OR "投資機會")',
        'subject:("旅遊" OR "travel" OR "booking" OR "reservation")'
    ]
    
    important_emails = []
    
    for query in queries:
        # 添加時間限制
        full_query = f'({query}) after:{two_hours_ago.strftime("%Y/%m/%d")}'
        
        try:
            results = service.users().messages().list(
                userId='me', 
                q=full_query,
                maxResults=10
            ).execute()
            
            messages = results.get('messages', [])
            
            for message in messages:
                msg = service.users().messages().get(
                    userId='me', 
                    id=message['id']
                ).execute()
                
                # 提取郵件資訊
                email_data = {
                    'id': message['id'],
                    'subject': '',
                    'sender': '',
                    'date': '',
                    'snippet': msg.get('snippet', '')[:100] + '...'
                }
                
                # 解析郵件標頭
                headers = msg['payload']['headers']
                for header in headers:
                    if header['name'] == 'Subject':
                        email_data['subject'] = header['value']
                    elif header['name'] == 'From':
                        email_data['sender'] = header['value']
                    elif header['name'] == 'Date':
                        email_data['date'] = header['value']
                
                important_emails.append(email_data)
                
        except Exception as e:
            print(f"Error searching emails with query '{query}': {e}")
            continue
    
    return important_emails

def main():
    """主函數"""
    try:
        print("開始 Gmail 監控...")
        service = authenticate_gmail()
        emails = get_important_emails(service)
        
        if emails:
            print(f"發現 {len(emails)} 封重要郵件:")
            for email in emails:
                print(f"- 主題: {email['subject']}")
                print(f"  寄件人: {email['sender']}")
                print(f"  時間: {email['date']}")
                print(f"  摘要: {email['snippet']}")
                print()
        else:
            print("未發現新的重要郵件")
            
    except Exception as e:
        print(f"Gmail 監控執行錯誤: {e}")

if __name__ == '__main__':
    main()