#!/usr/bin/env python3
"""
Gmail 瀏覽器自動化監控腳本
使用 Playwright 模擬人類操作登入 Gmail 並檢查重要郵件
"""

from playwright.sync_api import sync_playwright
import time
import json
from datetime import datetime
import os

class GmailBrowserMonitor:
    def __init__(self):
        self.email = "jack.sc.yang@gmail.com"
        self.password = "TanyaHuang1129"
        self.chrome_path = "/usr/bin/google-chrome"
        # 使用用戶現有的 Chrome 設定檔（如果已登入 Gmail）
        self.user_data_dir = "/home/admin/.config/google-chrome/Default"
        
    def check_important_emails(self, page):
        """掃描未讀郵件並識別重要類型"""
        important_emails = {
            "信用卡/帳單": [],
            "投資相關": [],
            "旅遊相關": [],
            "重要通知": []
        }
        
        # 關鍵字過濾
        keywords = {
            "信用卡/帳單": ["信用卡", "帳單", "對帳單", "中信", "富邦", "刷卡", "繳款"],
            "投資相關": ["股票", "證券", "基金", "ETF", "交易", "股息", "股利"],
            "旅遊相關": ["機票", "飯店", "訂房", "trip", "booking", "airline"],
            "重要通知": ["安全", "密碼", "驗證", "security", "password", "verify"]
        }
        
        try:
            # 等待郵件列表載入
            page.wait_for_selector('div[role="listitem"]', timeout=10000)
            
            # 獲取未讀郵件
            email_elements = page.query_selector_all('div[role="listitem"]')
            
            for email_elem in email_elements[:20]:  # 檢查前 20 封郵件
                try:
                    # 檢查是否為未讀郵件
                    if 'aria-label' in email_elem.get_attribute('outerHTML'):
                        aria_label = email_elem.get_attribute('aria-label')
                        
                        # 檢查是否為未讀
                        if '未讀' in aria_label or 'unread' in aria_label.lower():
                            # 提取郵件資訊
                            subject_elem = email_elem.query_selector('span span')
                            sender_elem = email_elem.query_selector('span[role="gridcell"]:first-child')
                            
                            if subject_elem and sender_elem:
                                subject = subject_elem.inner_text()
                                sender = sender_elem.inner_text()
                                
                                # 分類郵件
                                for category, kw_list in keywords.items():
                                    for kw in kw_list:
                                        if kw.lower() in subject.lower() or kw.lower() in sender.lower():
                                            important_emails[category].append({
                                                "subject": subject,
                                                "sender": sender,
                                                "time": datetime.now().strftime("%H:%M")
                                            })
                                            break
                except:
                    continue
                    
        except Exception as e:
            print(f"掃描郵件失敗：{e}")
            
        return important_emails
    
    def run(self, need_auth_code=None):
        """執行 Gmail 監控"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 開始 Gmail 監控...")
        
        with sync_playwright() as p:
            import os
            # 設置正確的 DISPLAY（X11）
            os.environ['DISPLAY'] = ':1'
            
            # 啟動 Chrome 瀏覽器（GUI 模式，可以處理密碼和認證碼）
            browser = p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False,  # GUI 模式，顯示瀏覽器窗口
                executable_path="/usr/bin/google-chrome",
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--start-maximized',
                    '--disable-gpu'
                ],
                slow_mo=1000  # 放慢操作速度，模擬人類
            )
            
            page = browser.pages[0] if browser.pages else browser.new_page()
            
            # 開啟 Gmail
            print("開啟 Gmail...")
            page.goto("https://mail.google.com/mail/u/0/#inbox", wait_until="networkidle")
            time.sleep(3)
            
            # 檢查是否已登入
            try:
                # 嘗試尋找郵件列表
                page.wait_for_selector('div[role="listitem"]', timeout=5000)
                print("✓ 已登入 Gmail")
                
                # 掃描郵件
                print("掃描未讀郵件...")
                important_emails = self.check_important_emails(page)
                
                # 生成摘要
                summary = self.generate_summary(important_emails)
                print(summary)
                
                browser.close()
                return {"status": "success", "summary": summary}
                
            except:
                # 未登入，需要登入
                print("需要登入 Gmail...")
                
                # 輸入帳號
                try:
                    email_input = page.wait_for_selector('input[type="email"]', timeout=5000)
                    email_input.fill(self.email)
                    time.sleep(1)
                    
                    # 點擊下一步
                    next_buttons = page.query_selector_all('button[type="button"]')
                    for btn in next_buttons:
                        btn_text = btn.inner_text()
                        if '下一步' in btn_text or 'Next' in btn_text:
                            btn.click()
                            break
                    time.sleep(5)  # 等待頁面轉換
                    
                    # 檢查是否需要手機認證
                    try:
                        # 檢查是否有認證碼輸入框
                        code_input = page.query_selector('input[type="text"]')
                        if code_input:
                            input_label = code_input.get_attribute('aria-label') or ''
                            if 'code' in input_label.lower() or '驗證' in input_label or '驗證碼' in input_label:
                                if need_auth_code:
                                    print(f"需要手機認證碼，使用提供的認證碼：{need_auth_code}")
                                    code_input.fill(need_auth_code)
                                    time.sleep(1)
                                    
                                    # 提交認證碼
                                    submit_buttons = page.query_selector_all('button[type="button"]')
                                    for btn in submit_buttons:
                                        btn_text = btn.inner_text()
                                        if '下一步' in btn_text or 'Next' in btn_text or 'Verify' in btn_text:
                                            btn.click()
                                            break
                                    time.sleep(5)
                                else:
                                    print("⚠️ 需要手機認證碼！請提供認證碼。")
                                    browser.close()
                                    return {"status": "need_auth_code", "message": "需要手機認證碼"}
                    except Exception as e:
                        print(f"認證碼檢查失敗：{e}")
                        pass
                    
                    # 輸入密碼（使用更精確的選擇器）
                    try:
                        # 等待密碼輸入框出現（Gmail 有多個 password 輸入框）
                        page.wait_for_function("""
                            () => {
                                const inputs = document.querySelectorAll('input[type="password"]');
                                for (let input of inputs) {
                                    if (input.name === 'password' && !input.hasAttribute('aria-hidden')) {
                                        return input;
                                    }
                                }
                                return null;
                            }
                        """, timeout=10000)
                        
                        # 找到正確的密碼輸入框
                        password_input = page.query_selector('input[type="password"][name="password"]:not([aria-hidden="true"])')
                        if not password_input:
                            password_inputs = page.query_selector_all('input[type="password"]')
                            for inp in password_inputs:
                                if not inp.get_attribute('aria-hidden'):
                                    password_input = inp
                                    break
                        
                        if password_input:
                            print("找到密碼輸入框，輸入密碼...")
                            password_input.fill(self.password)
                            time.sleep(2)
                            
                            # 點擊下一步
                            next_buttons = page.query_selector_all('button[type="button"]')
                            for btn in next_buttons:
                                btn_text = btn.inner_text()
                                if '下一步' in btn_text or 'Next' in btn_text:
                                    btn.click()
                                    break
                            time.sleep(5)
                        else:
                            print("找不到密碼輸入框")
                            browser.close()
                            return {"status": "error", "message": "找不到密碼輸入框"}
                        
                        # 等待郵件列表載入
                        page.wait_for_selector('div[role="listitem"]', timeout=10000)
                        print("✓ 登入成功")
                        
                        # 掃描郵件
                        print("掃描未讀郵件...")
                        important_emails = self.check_important_emails(page)
                        
                        # 生成摘要
                        summary = self.generate_summary(important_emails)
                        print(summary)
                        
                        browser.close()
                        return {"status": "success", "summary": summary}
                        
                    except Exception as e:
                        print(f"密碼輸入失敗：{e}")
                        browser.close()
                        return {"status": "error", "message": f"登入失敗：{str(e)}"}
                        
                except Exception as e:
                    print(f"帳號輸入失敗：{e}")
                    browser.close()
                    return {"status": "error", "message": f"登入失敗：{str(e)}"}
    
    def generate_summary(self, important_emails):
        """生成郵件摘要"""
        summary = "## 📧 Gmail 監控結果\n\n"
        
        total_count = sum(len(emails) for emails in important_emails.values())
        
        if total_count == 0:
            summary += "✅ 未發現重要未讀郵件\n"
        else:
            summary += f"共發現 **{total_count}** 封重要未讀郵件\n\n"
            
            for category, emails in important_emails.items():
                if emails:
                    emoji = {
                        "信用卡/帳單": "💳",
                        "投資相關": "📈",
                        "旅遊相關": "✈️",
                        "重要通知": "⚠️"
                    }.get(category, "📧")
                    
                    summary += f"{emoji} **{category}** ({len(emails)} 封):\n"
                    for email in emails[:3]:  # 最多顯示 3 封
                        summary += f"  • {email['subject']} ({email['sender']})\n"
                    if len(emails) > 3:
                        summary += f"  • 還有 {len(emails) - 3} 封...\n"
                    summary += "\n"
        
        summary += f"\n**檢查時間**: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        return summary


if __name__ == "__main__":
    import sys
    
    auth_code = sys.argv[1] if len(sys.argv) > 1 else None
    
    monitor = GmailBrowserMonitor()
    result = monitor.run(need_auth_code=auth_code)
    
    print("\n=== 最終結果 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
