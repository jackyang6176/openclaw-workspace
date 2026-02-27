#!/usr/bin/env python3
"""
Google Calendar 提醒腳本
檢查即將到來的事件並發送 Discord 通知
"""

import json
from datetime import datetime, timedelta
import subprocess

def check_upcoming_events():
    """模擬從 Google Calendar 讀取事件（實際應用中會使用 API 或瀏覽器自動化）"""
    
    # 這裡是從目前讀取到的行事曆資料
    events = [
        {
            "date": "2026-02-19",
            "end_date": "2026-02-22",
            "title": "🏕️ 武陵農場露營 - 春節假期",
            "calendar": "家庭",
            "type": "all_day"
        },
        {
            "date": "2026-02-25",
            "title": "💳 花旗信用卡繳費",
            "calendar": "Jack and Tanya Calendar",
            "type": "all_day"
        }
    ]
    
    today = datetime.now().date()
    reminders = []
    
    for event in events:
        event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
        days_until = (event_date - today).days
        
        # 提前 1 天和當天提醒
        if days_until in [0, 1]:
            reminders.append({
                "title": event["title"],
                "date": event["date"],
                "days_until": days_until,
                "calendar": event["calendar"]
            })
    
    return reminders

def send_discord_reminder(reminders):
    """發送 Discord 提醒"""
    if not reminders:
        print("今天沒有需要提醒的事件")
        return
    
    message = "📅 **行事曆提醒**\n\n"
    
    for r in reminders:
        if r["days_until"] == 0:
            message += f"🔔 **今天**: {r['title']}\n"
        else:
            message += f"⏰ **明天**: {r['title']}\n"
        message += f"   📆 日曆: {r['calendar']}\n\n"
    
    # 使用 openclaw 命令發送 Discord 消息
    try:
        result = subprocess.run(
            ["openclaw", "message", "send", "--to", "user:1467170004477935811", "--message", message],
            capture_output=True,
            text=True
        )
        print(f"提醒已發送: {result.returncode}")
    except Exception as e:
        print(f"發送失敗: {e}")

if __name__ == "__main__":
    reminders = check_upcoming_events()
    send_discord_reminder(reminders)
