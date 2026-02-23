#!/usr/bin/env python3
"""
Jmail.world Email Scraper (Browser-based)
==========================================
A comprehensive script to scrape Jeffrey Epstein's emails from jmail.world using browser automation

This version uses Playwright to properly handle JavaScript-rendered content.

Author: Created for dataset collection
License: MIT
"""

import asyncio
import json
import csv
import re
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
import argparse
import logging

try:
    from playwright.async_api import async_playwright, Page
except ImportError:
    print("Error: playwright is not installed.")
    print("Install it with: pip install playwright")
    print("Then run: playwright install")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JmailBrowserScraper:
    """
    Browser-based scraper for jmail.world email data
    
    Uses Playwright to properly handle JavaScript rendering and extract
    embedded Next.js data from the page.
    """
    
    BASE_URL = "https://jmail.world"
    
    def __init__(self, output_dir: str = "jmail_data", delay: float = 2.0, headless: bool = True):
        """
        Initialize the browser scraper
        
        Args:
            output_dir: Directory to save scraped data
            delay: Delay between page loads in seconds
            headless: Run browser in headless mode
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.delay = delay
        self.headless = headless
        
    async def extract_threads_from_page(self, page: Page) -> List[Dict]:
        """
        Extract email thread data from the loaded page
        
        Args:
            page: Playwright page object
            
        Returns:
            List of thread dictionaries
        """
        try:
            # Wait for page to be fully loaded
            await page.wait_for_load_state('networkidle')
            
            # Execute JavaScript to extract thread data from Next.js payload
            threads = await page.evaluate("""
                () => {
                    // Find all script tags
                    const scripts = Array.from(document.querySelectorAll('script'));
                    
                    // Find the large script containing thread data
                    for (const script of scripts) {
                        const content = script.textContent;
                        
                        // Look for the script with initialData and threads
                        if (content.includes('"initialData"') && content.includes('"threads":[')) {
                            try {
                                // Extract the JSON data from Next.js format
                                // Format: self.__next_f.push([1,"...escaped json..."])
                                const match = content.match(/self\\.__next_f\\.push\\(\\[1,"(.+?)"\\]\\)/);
                                if (!match) continue;
                                
                                let jsonStr = match[1];
                                
                                // Unescape the string
                                jsonStr = jsonStr
                                    .replace(/\\\\u/g, '\\u')
                                    .replace(/\\\\"/g, '"')
                                    .replace(/\\\\n/g, '')
                                    .replace(/\\\\\\\\/g, '\\\\');
                                
                                // Find initialData object
                                const initDataMatch = jsonStr.match(/"initialData":\\s*({[^}]*"threads":\\s*\\[[^\\]]+\\][^}]*})/);
                                if (!initDataMatch) continue;
                                
                                // Parse the data
                                const parsed = JSON.parse('{' + initDataMatch[0] + '}');
                                
                                if (parsed.initialData && parsed.initialData.threads) {
                                    return parsed.initialData.threads;
                                }
                            } catch (e) {
                                console.log('Parse error:', e);
                                continue;
                            }
                        }
                    }
                    
                    return [];
                }
            """)
            
            return threads if threads else []
            
        except Exception as e:
            logger.error(f"Error extracting threads: {e}")
            return []
    
    async def scrape_page(self, page: Page, page_num: int = 1) -> Dict:
        """
        Scrape a single page of emails
        
        Args:
            page: Playwright page object
            page_num: Page number (1-indexed)
            
        Returns:
            Dictionary containing thread data and metadata
        """
        url = f"{self.BASE_URL}/page/{page_num}" if page_num > 1 else self.BASE_URL
        
        logger.info(f"Scraping page {page_num} from {url}")
        
        try:
            # Navigate to the page
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait a moment for any dynamic content
            await asyncio.sleep(1)
            
            # Extract threads
            threads = await self.extract_threads_from_page(page)
            
            result = {
                'page': page_num,
                'threads': threads,
                'total_threads': len(threads),
                'scraped_at': datetime.utcnow().isoformat(),
            }
            
            logger.info(f"Successfully scraped {len(threads)} threads from page {page_num}")
            return result
            
        except Exception as e:
            logger.error(f"Error scraping page {page_num}: {e}")
            return {"threads": [], "page": page_num, "error": str(e)}
    
    async def scrape_all_pages(self, start_page: int = 1, end_page: Optional[int] = None) -> List[Dict]:
        """
        Scrape multiple pages of emails using browser automation
        
        Args:
            start_page: Starting page number
            end_page: Ending page number (None = scrape until no more data)
            
        Returns:
            List of all scraped threads
        """
        all_threads = []
        
        # Known from the site: ~7499 emails, ~100 per page = ~75 pages
        max_pages = end_page if end_page else 75
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            try:
                current_page = start_page
                
                while current_page <= max_pages:
                    result = await self.scrape_page(page, current_page)
                    
                    if not result['threads'] or 'error' in result:
                        logger.info(f"No more data or error at page {current_page}. Stopping.")
                        break
                    
                    all_threads.extend(result['threads'])
                    
                    # Save intermediate results
                    self.save_threads_to_json(
                        all_threads,
                        f"threads_page_{start_page}_to_{current_page}.json"
                    )
                    
                    logger.info(f"Progress: {len(all_threads)} total threads scraped")
                    
                    current_page += 1
                    
                    # Respectful delay between requests
                    if current_page <= max_pages:
                        await asyncio.sleep(self.delay)
            
            finally:
                await browser.close()
        
        return all_threads
    
    def save_threads_to_json(self, threads: List[Dict], filename: str) -> None:
        """Save threads to JSON file"""
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(threads, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(threads)} threads to {output_path}")
    
    def save_threads_to_csv(self, threads: List[Dict], filename: str) -> None:
        """Save threads to CSV file"""
        output_path = self.output_dir / filename
        
        if not threads:
            logger.warning("No threads to save to CSV")
            return
        
        # Get all unique keys
        fieldnames = set()
        for thread in threads:
            fieldnames.update(thread.keys())
        fieldnames = sorted(list(fieldnames))
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(threads)
        
        logger.info(f"Saved {len(threads)} threads to {output_path}")


async def main_async(args):
    """Async main function"""
    scraper = JmailBrowserScraper(
        output_dir=args.output_dir,
        delay=args.delay,
        headless=not args.show_browser
    )
    
    # Determine which pages to scrape
    if args.all:
        start_page, end_page = 1, 75
    elif args.pages:
        start_page, end_page = args.pages
    else:
        # Default: scrape first page only
        start_page, end_page = 1, 1
    
    # Scrape the emails
    logger.info(f"Starting scrape: pages {start_page} to {end_page}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Delay between requests: {args.delay}s")
    
    threads = await scraper.scrape_all_pages(start_page, end_page)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if args.format in ['json', 'both']:
        scraper.save_threads_to_json(threads, f'jmail_emails_{timestamp}.json')
    
    if args.format in ['csv', 'both']:
        scraper.save_threads_to_csv(threads, f'jmail_emails_{timestamp}.csv')
    
    logger.info(f"\n=== Scraping Complete ===")
    logger.info(f"Total threads scraped: {len(threads)}")
    logger.info(f"Output saved to: {args.output_dir}")


def main():
    """Main function to run the scraper"""
    parser = argparse.ArgumentParser(
        description='Scrape emails from jmail.world using browser automation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape first page (test run)
  python jmail_scraper_browser.py
  
  # Scrape pages 1-5
  python jmail_scraper_browser.py --pages 1 5
  
  # Scrape all pages
  python jmail_scraper_browser.py --all
  
  # Show browser window (not headless)
  python jmail_scraper_browser.py --show-browser --pages 1 2
  
  # Custom delay and output
  python jmail_scraper_browser.py --all --delay 3.0 --output-dir my_data
        """
    )
    
    parser.add_argument('--pages', nargs=2, type=int, metavar=('START', 'END'),
                       help='Scrape pages from START to END')
    parser.add_argument('--all', action='store_true',
                       help='Scrape all pages (1-75)')
    parser.add_argument('--delay', type=float, default=2.0,
                       help='Delay between requests in seconds (default: 2.0)')
    parser.add_argument('--output-dir', type=str, default='jmail_data',
                       help='Output directory for scraped data')
    parser.add_argument('--format', choices=['json', 'csv', 'both'], default='both',
                       help='Output format (default: both)')
    parser.add_argument('--show-browser', action='store_true',
                       help='Show browser window (non-headless mode)')
    
    args = parser.parse_args()
    
    # Run async scraper
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
