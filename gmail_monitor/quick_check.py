#!/usr/bin/env python3
"""
Gmail 快速檢查腳本 - 僅檢查是否有重要郵件
"""

import pickle
import os
import re
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def quick_check():
    """快速檢查重要郵件"""
    # 載入 token
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    
    # 建立 Gmail 服務
    service = build('gmail', 'v1', credentials=creds)
    
    # 檢查未讀郵件總數
    try:
        results = service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=1
        ).execute()
        unread_count = results.get('resultSizeEstimate', 0)
        print(f"📬 未讀郵件總數: {unread_count}")
        
        if unread_count == 0:
            print("\n📭 未發現重要未讀郵件\n\n系統已成功檢查您的 Gmail，目前沒有符合監控條件的重要郵件。")
            return
    except Exception as e:
        print(f"❌ 檢查未讀郵件失敗: {e}")
        return
    
    # 檢查重要郵件
    important_queries = [
        '信用卡',
        '帳單',
        '投資',
        '股票',
        '旅遊',
        '機票',
        '飯店',
        '重要通知'
    ]
    
    found_messages = []
    
    for query in important_queries:
        try:
            results = service.users().messages().list(
                userId='me',
                q=f'is:unread ({query})',
                maxResults=1
            ).execute()
            
            messages = results.get('messages', [])
            if messages:
                # 獲取第一封郵件的詳細資訊
                msg = service.users().messages().get(
                    userId='me',
                    id=messages[0]['id']
                ).execute()
                
                headers = msg['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '無主題')
                sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '未知寄件者')
                
                # 分析郵件類型
                email_type = "其他"
                if any(keyword in subject.lower() or keyword in sender.lower() for keyword in ['信用卡', '帳單']):
                    email_type = "💳 信用卡/帳單"
                elif any(keyword in subject.lower() or keyword in sender.lower() for keyword in ['投資', '股票', '證券', '基金']):
                    email_type = "📈 投資相關"
                elif any(keyword in subject.lower() or keyword in sender.lower() for keyword in ['旅遊', '機票', '飯店', 'booking', 'airbnb']):
                    email_type = "✈️ 旅遊相關"
                elif any(keyword in subject.lower() for keyword in ['重要通知', '緊急', '警告']):
                    email_type = "⚠️ 重要通知"
                
                found_messages.append({
                    'type': email_type,
                    'subject': subject,
                    'sender': sender
                })
                break  # 找到一封就停止
                
        except Exception as e:
            continue
    
    if found_messages:
        msg = found_messages[0]
        sender_clean = re.sub(r'<[^>]+>', '', msg['sender']).strip()
        print(f"\n📬 發現重要未讀郵件\n\n{msg['type']}:\n  • {msg['subject']} (來自: {sender_clean})\n\n💡 提醒：這封郵件可能包含重要的財務、投資或旅遊資訊，建議儘快查看。")
    else:
        print("\n📭 未發現重要未讀郵件\n\n系統已成功檢查您的 Gmail，目前沒有符合監控條件的重要郵件。")

if __name__ == "__main__":
    quick_check()