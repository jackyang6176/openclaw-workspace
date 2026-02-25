#!/usr/bin/env python3
"""
Intelligent Wait and Human-like Timing Module
Simulates human browsing behavior with random delays and adaptive waiting
"""

import time
import random
from typing import Optional, Callable, Any

class HumanTiming:
    """Human-like timing simulation for browser automation"""
    
    @staticmethod
    def random_delay(min_seconds: float = 0.5, max_seconds: float = 2.0) -> None:
        """Add random delay to simulate human thinking/reading time"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    @staticmethod
    def reading_pause(text_length: int) -> None:
        """Simulate reading time based on text length"""
        # Average reading speed: 200-300 words per minute
        # Assume 5 characters per word
        words = text_length // 5
        reading_time = words / 250  # 250 words per minute
        # Add some randomness
        actual_time = reading_time * random.uniform(0.8, 1.2)
        time.sleep(max(0.5, min(actual_time, 5.0)))  # Cap at 5 seconds
    
    @staticmethod
    def mouse_movement_delay() -> None:
        """Simulate natural mouse movement time"""
        delay = random.uniform(0.1, 0.5)
        time.sleep(delay)
    
    @staticmethod
    def typing_delay(char_count: int) -> None:
        """Simulate human typing speed"""
        # Average typing speed: 40-60 WPM (words per minute)
        # 5 chars per word = 200-300 chars per minute = 3-5 chars per second
        typing_speed = random.uniform(3, 5)  # chars per second
        typing_time = char_count / typing_speed
        # Add pauses and corrections
        total_time = typing_time * random.uniform(1.1, 1.5)
        time.sleep(total_time)

class IntelligentWait:
    """Intelligent waiting with multiple fallback strategies"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    def wait_for_element(self, check_func: Callable[[], bool], 
                        description: str = "element",
                        poll_interval: float = 0.5) -> bool:
        """Wait for element with intelligent polling"""
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < self.timeout:
            attempt += 1
            
            if check_func():
                return True
                
            # Adaptive polling - slower at first, faster later
            if attempt < 5:
                current_interval = poll_interval * random.uniform(1.0, 2.0)
            else:
                current_interval = poll_interval * random.uniform(0.5, 1.0)
                
            time.sleep(current_interval)
            
        return False
    
    def wait_for_page_load(self, initial_delay: float = 1.0) -> None:
        """Simulate human page loading behavior"""
        # Initial load time
        time.sleep(initial_delay)
        
        # Simulate scanning the page
        HumanTiming.random_delay(0.5, 1.5)
        
        # Check if page seems fully loaded
        # This would be enhanced with actual DOM checks in real implementation