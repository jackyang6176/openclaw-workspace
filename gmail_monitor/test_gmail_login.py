#!/usr/bin/env python3
"""簡單的 Gmail 登入測試"""

from playwright.sync_api import sync_playwright
import time

def test_gmail():
    with sync_playwright() as p:
        # 使用現有 Chrome 設定檔
        browser = p.chromium.launch_persistent_context(
            user_data_dir="/home/admin/.config/google-chrome/Default",
            headless=True,
            args=['--disable-gpu', '--no-sandbox']
        )
        
        page = browser.pages[0] if browser.pages else browser.new_page()
        
        print("訪問 Gmail...")
        page.goto("https://mail.google.com/mail/u/0/", wait_until="networkidle", timeout=30000)
        time.sleep(5)
        
        # 檢查是否已登入
        try:
            page.wait_for_selector('div[role="listitem"]', timeout=10000)
            print("✅ 已成功登入 Gmail！")
            
            # 獲取未讀郵件數量
            unread = page.query_selector_all('div[role="listitem"]')
            print(f"未讀郵件數量：{len(unread)}")
            
        except:
            print("❌ 未登入或無法訪問郵件列表")
            print(f"當前 URL: {page.url}")
        
        browser.close()

if __name__ == "__main__":
    test_gmail()
