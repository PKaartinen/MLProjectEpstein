#!/usr/bin/env python3
"""
Continue scraping from page 26 onwards
"""

import requests
import re
import json
import time
from pathlib import Path
from datetime import datetime

BASE_URL = "https://jmail.world"
OUTPUT_DIR = Path("jmail_data")
DELAY_BETWEEN_PAGES = 2.5
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

def extract_threads_from_html(html_content):
    """Extract threads from Next.js RSC format HTML with better error handling"""
    pattern = r'self\.__next_f\.push\(\[(.*?)\]\)'
    matches = re.findall(pattern, html_content, re.DOTALL)
    
    for match in matches:
        if 'threads' not in match or 'doc_id' not in match:
            continue
        
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
            max_iterations = len(decoded)  # Safety limit
            iterations = 0
            
            while pos < len(decoded) and bracket_count > 0 and iterations < max_iterations:
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
                iterations += 1
            
            if bracket_count == 0:
                threads_json = decoded[threads_start + len('"threads":'):pos]
                threads = json.loads(threads_json)
                return threads
        except json.JSONDecodeError as e:
            # Try alternative parsing - maybe the JSON is malformed
            try:
                # Sometimes there's extra escaping, try raw extraction
                threads_match = re.search(r'"threads":\s*(\[[^\]]+\])', match, re.DOTALL)
                if threads_match:
                    # Unescape manually
                    threads_str = threads_match.group(1)
                    threads_str = threads_str.replace('\\"', '"').replace('\\\\', '\\')
                    threads = json.loads(threads_str)
                    return threads
            except:
                pass
            continue
        except Exception:
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
    # Load existing data
    existing_file = OUTPUT_DIR / "jmail_complete_20260217_195906.json"
    with open(existing_file, 'r') as f:
        all_threads = json.load(f)
    
    print(f"Loaded {len(all_threads)} existing threads")
    print(f"Continuing from page 26...\n")
    
    successful_pages = 25
    failed_pages = []
    start_page = 26
    end_page = 75
    
    start_time = time.time()
    
    for page_num in range(start_page, end_page + 1):
        print(f"[{page_num}/{end_page}] Scraping page {page_num}...", end=' ', flush=True)
        
        threads = scrape_page(page_num)
        
        if threads is not None and len(threads) > 0:
            all_threads.extend(threads)
            successful_pages += 1
            print(f"✓ Got {len(threads)} threads (Total: {len(all_threads)})")
        elif threads is not None and len(threads) == 0:
            print(f"⚠ No threads found")
            # Continue anyway - might be temporary issue
        else:
            print(f"✗ Failed")
            failed_pages.append(page_num)
        
        # Save progress every 10 pages
        if page_num % 10 == 0:
            progress_file = OUTPUT_DIR / f"progress_page_{page_num}.json"
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(all_threads, f, indent=2, ensure_ascii=False)
            print(f"  💾 Progress saved")
        
        time.sleep(DELAY_BETWEEN_PAGES)
    
    elapsed = time.time() - start_time
    
    # Remove duplicates
    unique_threads = {t['doc_id']: t for t in all_threads}.values()
    unique_threads = list(unique_threads)
    
    print(f"\n{'='*70}")
    print(f"Time: {elapsed/60:.1f} min | Success: {successful_pages} | Total: {len(unique_threads)}")
    
    # Save final
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_file = OUTPUT_DIR / f"jmail_complete_final_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(unique_threads, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved to: {json_file}")
    
    # Save CSV
    import csv
    csv_file = OUTPUT_DIR / f"jmail_complete_final_{timestamp}.csv"
    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        all_keys = set()
        for thread in unique_threads:
            all_keys.update(thread.keys())
        writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
        writer.writeheader()
        writer.writerows(unique_threads)
    print(f"✓ Saved CSV to: {csv_file}")

if __name__ == '__main__':
    main()
