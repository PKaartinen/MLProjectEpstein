#!/usr/bin/env python3
"""
Complete jmail.world scraper - Extracts all email threads from all pages
"""

import requests
import re
import json
import time
from pathlib import Path
from datetime import datetime

# Configuration
BASE_URL = "https://jmail.world"
OUTPUT_DIR = Path("jmail_data")
DELAY_BETWEEN_PAGES = 2.5  # seconds - be respectful
TOTAL_PAGES = 75  # Based on site analysis
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

def extract_threads_from_html(html_content):
    """Extract threads from Next.js RSC format HTML"""
    # Find all self.__next_f.push calls
    pattern = r'self\.__next_f\.push\(\[(.*?)\]\)'
    matches = re.findall(pattern, html_content, re.DOTALL)
    
    for match in matches:
        # Check if this chunk contains thread data
        if 'threads' in match and 'doc_id' in match:
            # Split to get JSON part
            parts = match.split(',', 1)
            if len(parts) < 2:
                continue
            
            chunk_json = parts[1].strip()
            
            try:
                # Decode the JSON-encoded string
                decoded = json.loads(chunk_json)
                
                # Find threads array
                threads_start = decoded.find('"threads":[')
                if threads_start == -1:
                    continue
                
                # Extract using bracket matching
                search_start = threads_start + len('"threads":[')
                bracket_count = 1
                pos = search_start
                in_string = False
                escape_next = False
                
                while pos < len(decoded) and bracket_count > 0:
                    char = decoded[pos]
                    
                    if escape_next:
                        escape_next = False
                    elif char == '\\':
                        escape_next = True
                    elif char == '"' and not escape_next:
                        in_string = not in_string
                    elif not in_string:
                        if char == '[':
                            bracket_count += 1
                        elif char == ']':
                            bracket_count -= 1
                    
                    pos += 1
                
                if bracket_count == 0:
                    threads_json = decoded[threads_start + len('"threads":'):pos]
                    threads = json.loads(threads_json)
                    return threads
            except (json.JSONDecodeError, Exception) as e:
                print(f'  ⚠ Warning: Could not parse chunk: {e}')
                continue
    
    return []

def scrape_page(page_num):
    """Scrape a single page"""
    url = f"{BASE_URL}/page/{page_num}" if page_num > 1 else BASE_URL
    
    try:
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=15)
        response.raise_for_status()
        
        threads = extract_threads_from_html(response.text)
        return threads
    except requests.RequestException as e:
        print(f'  ✗ Error fetching page: {e}')
        return None

def main():
    print("=" * 70)
    print(" JMAIL.WORLD COMPLETE SCRAPER")
    print("=" * 70)
    print(f"Target: {BASE_URL}")
    print(f"Pages to scrape: {TOTAL_PAGES}")
    print(f"Delay between requests: {DELAY_BETWEEN_PAGES}s")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 70)
    print()
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    all_threads = []
    successful_pages = 0
    failed_pages = []
    
    start_time = time.time()
    
    for page_num in range(1, TOTAL_PAGES + 1):
        print(f"[{page_num}/{TOTAL_PAGES}] Scraping page {page_num}...", end=' ', flush=True)
        
        threads = scrape_page(page_num)
        
        if threads is not None and len(threads) > 0:
            all_threads.extend(threads)
            successful_pages += 1
            print(f"✓ Got {len(threads)} threads (Total: {len(all_threads)})")
        elif threads is not None and len(threads) == 0:
            print(f"⚠ No threads found (might be end of data)")
            break  # Stop if we hit an empty page
        else:
            print(f"✗ Failed")
            failed_pages.append(page_num)
        
        # Save progress every 10 pages
        if page_num % 10 == 0:
            progress_file = OUTPUT_DIR / f"progress_page_{page_num}.json"
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(all_threads, f, indent=2, ensure_ascii=False)
            print(f"  💾 Progress saved to {progress_file}")
        
        # Rate limiting (except for last page)
        if page_num < TOTAL_PAGES:
            time.sleep(DELAY_BETWEEN_PAGES)
    
    elapsed = time.time() - start_time
    
    # Save final results
    print("\n" + "=" * 70)
    print(" SCRAPING COMPLETE")
    print("=" * 70)
    print(f"Time elapsed: {elapsed/60:.1f} minutes")
    print(f"Successful pages: {successful_pages}/{TOTAL_PAGES}")
    print(f"Total threads extracted: {len(all_threads)}")
    
    if failed_pages:
        print(f"Failed pages: {failed_pages}")
    
    # Remove duplicates by doc_id
    unique_threads = {t['doc_id']: t for t in all_threads}.values()
    unique_threads = list(unique_threads)
    print(f"Unique threads (after dedup): {len(unique_threads)}")
    
    # Save complete dataset
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_file = OUTPUT_DIR / f"jmail_complete_{timestamp}.json"
    csv_file = OUTPUT_DIR / f"jmail_complete_{timestamp}.csv"
    
    # Save JSON
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(unique_threads, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved JSON to: {json_file}")
    
    # Save CSV
    import csv
    if unique_threads:
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            # Get all possible keys
            all_keys = set()
            for thread in unique_threads:
                all_keys.update(thread.keys())
            
            writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
            writer.writeheader()
            writer.writerows(unique_threads)
        print(f"✓ Saved CSV to: {csv_file}")
    
    # Statistics
    print("\n=== Dataset Statistics ===")
    redacted = sum(1 for t in unique_threads if t.get('isRedacted'))
    print(f"Redacted emails: {redacted} ({redacted/len(unique_threads)*100:.1f}%)")
    print(f"Unredacted emails: {len(unique_threads) - redacted}")
    
    # By source
    sources = {}
    for t in unique_threads:
        source = t.get('email_drop_id', 'unknown')
        sources[source] = sources.get(source, 0) + 1
    print("\nThreads by source:")
    for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        print(f"  {source}: {count}")
    
    # Top starred
    top_starred = sorted(unique_threads, key=lambda t: t.get('starCount', 0), reverse=True)[:10]
    print("\n=== Top 10 Most Starred Threads ===")
    for i, thread in enumerate(top_starred, 1):
        subj = thread.get('subject', 'No subject')
        if len(subj) > 50:
            subj = subj[:47] + '...'
        stars = thread.get('starCount', 0)
        print(f"{i:2d}. ⭐{stars:4d} - {subj}")
    
    print("\n" + "=" * 70)
    print("✓ Scraping completed successfully!")
    print("=" * 70)

if __name__ == '__main__':
    main()
