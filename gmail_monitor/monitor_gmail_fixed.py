#!/usr/bin/env python3
"""
Gmail 監控主腳本 - 修復版本
監控重要郵件並生成通知摘要
"""

import pickle
import os
import re
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def get_important_emails():
    """獲取重要類型的未讀郵件"""
    # 載入 token
    if not os.path.exists('token.pickle'):
        return None, "❌ token.pickle 不存在"
    
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    
    # 刷新 token（如果需要）
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        else:
            return None, "❌ token 無效且無法刷新"
    
    # 建立 Gmail 服務
    service = build('gmail', 'v1', credentials=creds)
    
    # 定義重要郵件類型的搜尋查詢
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
    
    all_messages = []
    
    # 搜尋每種類型的郵件
    for query in important_queries:
        try:
            results = service.users().messages().list(
                userId='me',
                q=f'is:unread ({query})',
                maxResults=10
            ).execute()
            
            messages = results.get('messages', [])
            if messages:
                # 獲取郵件詳細資訊
                for msg_info in messages[:3]:  # 每類最多取3封
                    msg = service.users().messages().get(
                        userId='me',
                        id=msg_info['id']
                    ).execute()
                    
                    headers = msg['payload']['headers']
                    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '無主題')
                    sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '未知寄件者')
                    date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '未知日期')
                    
                    # 分析郵件類型
                    email_type = "其他"
                    subject_lower = subject.lower()
                    sender_lower = sender.lower()
                    
                    if any(keyword in subject_lower or keyword in sender_lower for keyword in ['信用卡', '帳單']):
                        email_type = "💳 信用卡/帳單"
                    elif any(keyword in subject_lower or keyword in sender_lower for keyword in ['投資', '股票', '證券', '基金']):
                        email_type = "📈 投資相關"
                    elif any(keyword in subject_lower or keyword in sender_lower for keyword in ['旅遊', '機票', '飯店', 'booking', 'airbnb']):
                        email_type = "✈️ 旅遊相關"
                    elif any(keyword in subject_lower for keyword in ['重要通知', '緊急', '警告']):
                        email_type = "⚠️ 重要通知"
                    
                    all_messages.append({
                        'type': email_type,
                        'subject': subject,
                        'sender': sender,
                        'date': date,
                        'id': msg_info['id']
                    })
                    
        except Exception as e:
            continue  # 跳過錯誤，繼續處理其他查詢
    
    return all_messages, None

def generate_summary(messages):
    """生成郵件摘要"""
    if not messages:
        return "📭 未發現重要未讀郵件\n\n系統已成功檢查您的 Gmail，目前沒有符合監控條件的重要郵件。"
    
    # 按類型分組
    grouped = {}
    for msg in messages:
        msg_type = msg['type']
        if msg_type not in grouped:
            grouped[msg_type] = []
        grouped[msg_type].append(msg)
    
    summary = f"📬 發現 {len(messages)} 封重要未讀郵件\n\n"
    
    for msg_type, msgs in grouped.items():
        summary += f"{msg_type} ({len(msgs)} 封):\n"
        for msg in msgs[:2]:  # 每類最多顯示2封
            # 清理寄件者格式
            sender_clean = re.sub(r'<[^>]+>', '', msg['sender']).strip()
            summary += f"  • {msg['subject']} (來自: {sender_clean})\n"
        if len(msgs) > 2:
            summary += f"  • 還有 {len(msgs) - 2} 封...\n"
        summary += "\n"
    
    summary += "💡 提醒：這些郵件可能包含重要的財務、投資或旅遊資訊，建議儘快查看。"
    return summary

def main():
    """主函數"""
    messages, error = get_important_emails()
    
    if error:
        print(f"❌ Gmail 監控錯誤: {error}")
        return
    
    summary = generate_summary(messages)
    print(summary)

if __name__ == "__main__":
    main()