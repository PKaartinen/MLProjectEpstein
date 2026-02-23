#!/usr/bin/env python3
"""
Jmail.world Email Scraper
=========================
A comprehensive script to scrape Jeffrey Epstein's emails from jmail.world

The site presents emails in a Gmail-like interface with pagination.
Data is loaded server-side and embedded in the HTML response.

Author: Created for dataset collection
License: MIT
"""

import requests
import json
import time
import csv
import re
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JmailScraper:
    """
    Scraper for jmail.world email data
    
    The site uses Next.js with server-side rendering. Email data is embedded
    in the initial HTML payload as JSON within script tags.
    """
    
    BASE_URL = "https://jmail.world"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    def __init__(self, output_dir: str = "jmail_data", delay: float = 2.0):
        """
        Initialize the scraper
        
        Args:
            output_dir: Directory to save scraped data
            delay: Delay between requests in seconds (be respectful!)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        
    def extract_json_from_html(self, html: str) -> Optional[Dict]:
        """
        Extract embedded JSON data from Next.js HTML
        
        Next.js embeds data in script tags with self.__next_f.push([...])
        We need to find and parse these JSON payloads.
        """
        try:
            # Look for the main data payload containing email threads
            # Pattern: self.__next_f.push([1,"...json data..."])
            pattern = r'self\.__next_f\.push\(\[1,"([^"]+)"\]\)'
            matches = re.findall(pattern, html)
            
            for match in matches:
                # Unescape the JSON string
                unescaped = match.encode().decode('unicode_escape')
                
                # Try to find thread data in this payload
                if '"threads":[' in unescaped or '"initialData"' in unescaped:
                    # Extract the JSON object
                    try:
                        # Find the JSON object containing threads
                        json_start = unescaped.find('{')
                        json_end = unescaped.rfind('}') + 1
                        if json_start != -1 and json_end > json_start:
                            data = json.loads(unescaped[json_start:json_end])
                            if 'threads' in data or ('initialData' in data and 'threads' in data.get('initialData', {})):
                                return data
                    except json.JSONDecodeError:
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting JSON from HTML: {e}")
            return None
    
    def scrape_page(self, page: int = 1, category: str = "primary") -> Dict:
        """
        Scrape a single page of emails
        
        Args:
            page: Page number (1-indexed)
            category: Email category (primary, promotions, etc.)
            
        Returns:
            Dictionary containing thread data and metadata
        """
        url = f"{self.BASE_URL}/page/{page}" if page > 1 else self.BASE_URL
        
        logger.info(f"Scraping page {page} from {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Extract JSON data from HTML
            data = self.extract_json_from_html(response.text)
            
            if not data:
                logger.warning(f"No data found on page {page}")
                return {"threads": [], "page": page, "error": "No data extracted"}
            
            # Extract thread information
            threads = []
            thread_list = data.get('threads', [])
            
            # Handle nested structure
            if not thread_list and 'initialData' in data:
                thread_list = data['initialData'].get('threads', [])
            
            for thread in thread_list:
                thread_info = {
                    'doc_id': thread.get('doc_id'),
                    'first_message_id': thread.get('firstMessageId'),
                    'subject': thread.get('subject'),
                    'sender_name': thread.get('latest_sender_name'),
                    'sender_email': thread.get('latest_sender_email'),
                    'date': thread.get('formatted_date'),
                    'preview': thread.get('preview'),
                    'message_count': thread.get('count', 1),
                    'attachments': thread.get('attachments', 0),
                    'star_count': thread.get('starCount', 0),
                    'unredact_count': thread.get('unredactCount', 0),
                    'email_drop_id': thread.get('email_drop_id'),
                    'is_from_epstein': thread.get('latest_is_from_epstein', False),
                    'is_redacted': thread.get('isRedacted', False),
                }
                threads.append(thread_info)
            
            result = {
                'page': page,
                'threads': threads,
                'total_threads': len(threads),
                'scraped_at': datetime.utcnow().isoformat(),
            }
            
            logger.info(f"Successfully scraped {len(threads)} threads from page {page}")
            return result
            
        except requests.RequestException as e:
            logger.error(f"Request error on page {page}: {e}")
            return {"threads": [], "page": page, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error on page {page}: {e}")
            return {"threads": [], "page": page, "error": str(e)}
    
    def scrape_thread_detail(self, doc_id: str) -> Optional[Dict]:
        """
        Scrape detailed information for a specific email thread
        
        Args:
            doc_id: Document ID of the thread
            
        Returns:
            Detailed thread information including full email content
        """
        url = f"{self.BASE_URL}/thread/{doc_id}"
        
        logger.info(f"Scraping thread detail: {doc_id}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse HTML for thread details
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract thread data (structure depends on actual page layout)
            # This is a placeholder - would need to inspect actual thread page
            thread_detail = {
                'doc_id': doc_id,
                'url': url,
                'html_content': response.text[:1000],  # Store sample
                'scraped_at': datetime.utcnow().isoformat(),
            }
            
            return thread_detail
            
        except Exception as e:
            logger.error(f"Error scraping thread {doc_id}: {e}")
            return None
    
    def scrape_all_pages(self, start_page: int = 1, end_page: Optional[int] = None) -> List[Dict]:
        """
        Scrape multiple pages of emails
        
        Args:
            start_page: Starting page number
            end_page: Ending page number (None = scrape until no more data)
            
        Returns:
            List of all scraped threads
        """
        all_threads = []
        current_page = start_page
        
        # Known from the site: 7499 emails, 100 per page = 75 pages
        max_pages = end_page if end_page else 75
        
        while current_page <= max_pages:
            result = self.scrape_page(current_page)
            
            if not result['threads'] or 'error' in result:
                logger.info(f"No more data or error at page {current_page}. Stopping.")
                break
            
            all_threads.extend(result['threads'])
            
            # Save intermediate results
            self.save_threads_to_json(all_threads, f"threads_page_{start_page}_to_{current_page}.json")
            
            logger.info(f"Progress: {len(all_threads)} total threads scraped")
            
            current_page += 1
            
            # Respectful delay between requests
            if current_page <= max_pages:
                time.sleep(self.delay)
        
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
        
        # Get all unique keys from all threads
        fieldnames = set()
        for thread in threads:
            fieldnames.update(thread.keys())
        fieldnames = sorted(list(fieldnames))
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(threads)
        
        logger.info(f"Saved {len(threads)} threads to {output_path}")
    
    def get_site_statistics(self) -> Dict:
        """
        Get overall statistics about the email dataset
        """
        logger.info("Fetching site statistics...")
        
        try:
            response = self.session.get(self.BASE_URL, timeout=30)
            response.raise_for_status()
            
            data = self.extract_json_from_html(response.text)
            
            if data:
                initial_data = data.get('initialData', data)
                stats = {
                    'total_emails': initial_data.get('total', 0),
                    'total_pages': initial_data.get('totalPages', 0),
                    'promotions_count': initial_data.get('promotionsInfo', {}).get('count', 0),
                    'scraped_at': datetime.utcnow().isoformat(),
                }
                return stats
            
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching statistics: {e}")
            return {}


def main():
    """Main function to run the scraper"""
    parser = argparse.ArgumentParser(
        description='Scrape emails from jmail.world',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape first 5 pages
  python jmail_scraper.py --pages 1 5
  
  # Scrape all pages with custom delay
  python jmail_scraper.py --all --delay 3.0
  
  # Get site statistics
  python jmail_scraper.py --stats
        """
    )
    
    parser.add_argument('--pages', nargs=2, type=int, metavar=('START', 'END'),
                       help='Scrape pages from START to END')
    parser.add_argument('--all', action='store_true',
                       help='Scrape all pages (1-75)')
    parser.add_argument('--stats', action='store_true',
                       help='Get site statistics')
    parser.add_argument('--delay', type=float, default=2.0,
                       help='Delay between requests in seconds (default: 2.0)')
    parser.add_argument('--output-dir', type=str, default='jmail_data',
                       help='Output directory for scraped data')
    parser.add_argument('--format', choices=['json', 'csv', 'both'], default='both',
                       help='Output format (default: both)')
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = JmailScraper(output_dir=args.output_dir, delay=args.delay)
    
    # Get statistics if requested
    if args.stats:
        stats = scraper.get_site_statistics()
        print("\n=== Jmail.world Statistics ===")
        print(json.dumps(stats, indent=2))
        return
    
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
    
    threads = scraper.scrape_all_pages(start_page, end_page)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if args.format in ['json', 'both']:
        scraper.save_threads_to_json(threads, f'jmail_emails_{timestamp}.json')
    
    if args.format in ['csv', 'both']:
        scraper.save_threads_to_csv(threads, f'jmail_emails_{timestamp}.csv')
    
    logger.info(f"\n=== Scraping Complete ===")
    logger.info(f"Total threads scraped: {len(threads)}")
    logger.info(f"Output saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
