#!/usr/bin/env python3
"""
Simple Jmail Scraper - Working Implementation
==============================================
A straightforward scraper that extracts visible email data from jmail.world

This scraper uses Selenium as a simple, reliable alternative.
"""

import time
import json
import csv
from pathlib import Path
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
except ImportError:
    print("Error: selenium is not installed.")
    print("Install it with: pip install selenium")
    exit(1)

def scrape_jmail_page(driver, page_num):
    """Scrape a single page of jmail.world"""
    url = f"https://jmail.world/page/{page_num}" if page_num > 1 else "https://jmail.world"
    
    print(f"Scraping page {page_num}: {url}")
    
    driver.get(url)
    
    # Wait for email list to load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "inbox-container"))
        )
        time.sleep(2)  # Extra wait for JavaScript
    except:
        print(f"Timeout waiting for page {page_num} to load")
        return []
    
    # Get all email rows
    # We'll extract the visible text since the data structure is complex
    emails = []
    
    try:
        # Try to find email rows by various selectors
        rows = driver.find_elements(By.CSS_SELECTOR, "a[href^='/thread/']")
        
        for row in rows:
            try:
                # Extract href to get doc_id
                href = row.get_attribute('href')
                doc_id = href.split('/thread/')[-1] if '/thread/' in href else ''
                
                # Get all text content
                text = row.text
                
                email_data = {
                    'doc_id': doc_id,
                    'url': href,
                    'text_content': text,
                    'page': page_num,
                    'scraped_at': datetime.utcnow().isoformat()
                }
                
                emails.append(email_data)
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
        
        print(f"Found {len(emails)} emails on page {page_num}")
        
    except Exception as e:
        print(f"Error extracting emails from page {page_num}: {e}")
    
    return emails

def main():
    """Main scraping function"""
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in background
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    
    # Create output directory
    output_dir = Path('jmail_data')
    output_dir.mkdir(exist_ok=True)
    
    # Initialize driver
    print("Initializing Chrome driver...")
    driver = webdriver.Chrome(options=chrome_options)
    
    all_emails = []
    
    try:
        # Scrape first 3 pages as a test
        for page in range(1, 4):
            emails = scrape_jmail_page(driver, page)
            all_emails.extend(emails)
            
            # Respectful delay
            time.sleep(3)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as JSON
        json_file = output_dir / f"jmail_simple_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(all_emails, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(all_emails)} emails to {json_file}")
        
        # Save as CSV
        if all_emails:
            csv_file = output_dir / f"jmail_simple_{timestamp}.csv"
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=all_emails[0].keys())
                writer.writeheader()
                writer.writerows(all_emails)
            print(f"Saved to {csv_file}")
        
    finally:
        driver.quit()
        print("\nScraping complete!")

if __name__ == "__main__":
    main()
