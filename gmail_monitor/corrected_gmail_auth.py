#!/usr/bin/env python3
"""
Gmail 認證腳本 - 修正版本
使用手動授權碼完成 OAuth 2.0 認證
"""

import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API 權限範圍
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_with_auth_code(auth_code):
    """使用授權碼完成認證"""
    creds = None
    
    # 讀取 credentials.json
    if os.path.exists('credentials.json'):
        # 建立 flow 物件
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        
        # 手動設定重定向 URI
        flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
        
        try:
            # 使用授權碼獲取 token
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            
            # 保存 token
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
            
            print("✅ Gmail 認證成功！")
            print("✅ token.pickle 已生成")
            return True
            
        except Exception as e:
            print(f"❌ 認證失敗: {str(e)}")
            return False
    else:
        print("❌ 找不到 credentials.json 文件")
        return False

def main():
    """主函數"""
    print("📧 Gmail 認證系統啟動...")
    
    # 讀取授權碼
    if os.path.exists('auth_code.txt'):
        with open('auth_code.txt', 'r') as f:
            auth_code = f.read().strip()
        print(f"使用網路授權碼: {auth_code[:20]}...")
    else:
        print("❌ 找不到 auth_code.txt 文件")
        return
    
    # 執行認證
    if authenticate_with_auth_code(auth_code):
        print("🎉 Gmail 認證完成！監控系統已準備就緒。")
    else:
        print("❌ 認證失敗，請重新嘗試。")

if __name__ == '__main__':
    main()