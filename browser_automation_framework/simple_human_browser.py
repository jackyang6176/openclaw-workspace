#!/usr/bin/env python3
"""
Simple Human-like Browser Automation
Focus on reliability over complexity
"""

import time
import random
from datetime import datetime

def human_delay(min_seconds=1, max_seconds=3):
    """Simulate human-like delays"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)
    return delay

def human_scroll(browser, target_element=None):
    """Simulate natural scrolling behavior"""
    if target_element:
        # Scroll to element naturally
        browser.execute_script("arguments[0].scrollIntoView({behavior: 'smooth'});", target_element)
    else:
        # Random scroll
        scroll_amount = random.randint(200, 800)
        browser.execute_script(f"window.scrollBy(0, {scroll_amount});")
    
    human_delay(0.5, 1.5)

def extract_news_content(browser, source_name):
    """Extract news content with human-like behavior"""
    print(f"Extracting news from {source_name} with human-like behavior...")
    
    # Simulate human reading time
    human_delay(2, 4)
    
    # Try multiple selectors for robustness
    selectors = {
        'BBC': ['h3[data-testid="card-headline"]', 'h2[class*="headline"]', '.gs-c-promo-heading__title'],
        'Reuters': ['h3[data-testid="Heading"]', '.story-title', 'a[href*="/world/"] h3'],
        'AP': ['.Page-headline', 'h1', '.CardHeadline'],
        'CNN': ['h3[class*="headline"]', '.cd__headline', 'a[href*="/world/"] span']
    }
    
    content = []
    try:
        if source_name in selectors:
            for selector in selectors[source_name]:
                try:
                    elements = browser.find_elements("css selector", selector)
                    if elements:
                        for elem in elements[:3]:  # Limit to top 3 articles
                            text = elem.text.strip()
                            if text and len(text) > 20:  # Filter out short texts
                                content.append({
                                    'title': text,
                                    'source': source_name,
                                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                })
                        break
                except Exception as e:
                    continue
        
        # Simulate human interaction with page
        human_scroll(browser)
        human_delay(1, 2)
        
    except Exception as e:
        print(f"Error extracting from {source_name}: {e}")
    
    return content

def human_like_news_scraper():
    """Main function for human-like news scraping"""
    print("Starting human-like browser automation for international news...")
    
    # This will be integrated with the actual browser control
    # For now, return sample data to test the framework
    sample_news = [
        {
            'title': 'Human-like browser automation successfully implemented',
            'source': 'System Status',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    ]
    
    return sample_news