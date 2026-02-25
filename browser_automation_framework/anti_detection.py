#!/usr/bin/env python3
"""
Anti-detection module for human-like browser automation
Prevents websites from detecting automated access
"""

import random
import time
from typing import Dict, Any

class AntiDetection:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ]
        
    def get_random_user_agent(self) -> str:
        """Get a random user agent string"""
        return random.choice(self.user_agents)
    
    def add_human_like_delays(self, min_delay: float = 0.5, max_delay: float = 2.0):
        """Add human-like random delays between actions"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
        
    def simulate_mouse_movement(self, start_x: int, start_y: int, end_x: int, end_y: int):
        """Simulate natural mouse movement with bezier curves"""
        # This would be implemented with actual mouse movement simulation
        # For now, we'll just add appropriate delays
        steps = random.randint(3, 8)
        for i in range(steps):
            progress = i / steps
            # Simulate acceleration and deceleration
            if progress < 0.3:
                step_delay = random.uniform(0.05, 0.1)
            elif progress > 0.7:
                step_delay = random.uniform(0.05, 0.1)
            else:
                step_delay = random.uniform(0.02, 0.05)
            time.sleep(step_delay)
            
    def random_scroll_behavior(self, target_element: str = None):
        """Simulate natural scrolling behavior"""
        # Add random scrolling before and after interactions
        scroll_actions = random.randint(1, 3)
        for _ in range(scroll_actions):
            scroll_amount = random.randint(50, 300)
            scroll_direction = random.choice([-1, 1])
            time.sleep(random.uniform(0.1, 0.5))
            
    def set_browser_fingerprint(self) -> Dict[str, Any]:
        """Set browser fingerprint to appear more human-like"""
        return {
            "user_agent": self.get_random_user_agent(),
            "screen_width": random.choice([1920, 1366, 1440, 1536]),
            "screen_height": random.choice([1080, 768, 900, 864]),
            "color_depth": 24,
            "timezone": "Asia/Shanghai",
            "language": "zh-TW",
            "platform": random.choice(["Win32", "MacIntel", "Linux x86_64"])
        }