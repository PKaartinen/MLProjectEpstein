#!/usr/bin/env python3
"""
Live Puppeteer-based scraper for jmail.world
Uses MCP Puppeteer server to navigate and extract data
"""

import json
import re
import time
import os
from pathlib import Path

# Create output directory
output_dir = Path("jmail_data")
output_dir.mkdir(exist_ok=True)

def extract_threads_from_html(html_content):
    """Extract thread data from Next.js HTML payload"""
    # Pattern to find the threads array in the Next.js data
    # The data is in format: "threads":[{...},{...}]
    pattern = r'"threads":\s*(\[[^\]]*?\{[^}]*?"doc_id"[^}]*?\}[^\]]*?\])'
    
    matches = re.findall(pattern, html_content, re.DOTALL)
    
    if not matches:
        print("No threads found with primary pattern")
        # Try alternative pattern
        alt_pattern = r'"threads":\[(.*?)\](?=,"totalPages"|,"page")'
        matches = re.findall(alt_pattern, html_content, re.DOTALL)
    
    all_threads = []
    for match in matches:
        try:
            # Try to parse as JSON
            if not match.startswith('['):
                match = '[' + match + ']'
            
            # Handle escaped quotes
            match = match.replace('\\"', '"').replace('\\\\', '\\')
            
            threads = json.loads(match)
            all_threads.extend(threads)
            print(f"Extracted {len(threads)} threads from match")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Match preview: {match[:200]}...")
            continue
    
    return all_threads

def scrape_page_with_puppeteer_html(page_num=1):
    """
    Instructions for using Puppeteer MCP to scrape a page:
    
    1. Navigate to the page using puppeteer_navigate
    2. Use puppeteer_evaluate with: document.documentElement.outerHTML
    3. Save the returned HTML
    4. Parse with this function
    """
    print(f"\n=== INSTRUCTIONS FOR PAGE {page_num} ===")
    url = f"https://jmail.world/page/{page_num}" if page_num > 1 else "https://jmail.world/"
    print(f"1. Navigate: puppeteer_navigate(url='{url}')")
    print(f"2. Evaluate: puppeteer_evaluate(script='document.documentElement.outerHTML')")
    print(f"3. Save result to: jmail_data/page_{page_num}.html")
    print(f"4. Run: python3 live_puppeteer_scraper.py --parse page_{page_num}.html")
    

def parse_saved_html(filename):
    """Parse a saved HTML file and extract threads"""
    filepath = output_dir / filename
    
    if not filepath.exists():
        print(f"Error: File {filepath} not found")
        return None
    
    print(f"Reading HTML from {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    print(f"HTML file size: {len(html_content):,} characters")
    
    # Extract threads
    threads = extract_threads_from_html(html_content)
    
    if threads:
        # Save to JSON
        output_file = filepath.with_suffix('.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(threads, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Successfully extracted {len(threads)} threads")
        print(f"✓ Saved to: {output_file}")
        
        # Print sample thread
        if threads:
            print("\n=== Sample Thread ===")
            sample = threads[0]
            for key in ['doc_id', 'subject', 'sender_name', 'sender_email', 'formatted_date']:
                if key in sample:
                    print(f"{key}: {sample[key]}")
        
        return threads
    else:
        print("No threads extracted. Checking HTML structure...")
        # Look for key patterns
        if '"threads":' in html_content:
            print("✓ Found 'threads' key in HTML")
        if 'self.__next_f.push' in html_content:
            print("✓ Found Next.js flight data")
        if '"doc_id"' in html_content:
            print("✓ Found doc_id fields")
        
        # Save HTML snippet for debugging
        debug_file = output_dir / f"debug_{filename}.txt"
        with open(debug_file, 'w') as f:
            # Find and save relevant sections
            threads_idx = html_content.find('"threads":')
            if threads_idx > 0:
                f.write(html_content[threads_idx:threads_idx+2000])
        print(f"Saved debug snippet to {debug_file}")
        
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--parse":
        # Parse mode
        if len(sys.argv) < 3:
            print("Usage: python3 live_puppeteer_scraper.py --parse <filename>")
            sys.exit(1)
        
        filename = sys.argv[2]
        parse_saved_html(filename)
    else:
        # Instruction mode
        print("=" * 60)
        print("JMAIL PUPPETEER SCRAPING WORKFLOW")
        print("=" * 60)
        
        print("\nThis script works with the Puppeteer MCP server.")
        print("Follow these steps to scrape jmail.world:\n")
        
        # Generate instructions for first 3 pages
        for page_num in range(1, 4):
            scrape_page_with_puppeteer_html(page_num)
            print()
        
        print("=" * 60)
        print("\nAfter collecting HTML files, parse them with:")
        print("  python3 live_puppeteer_scraper.py --parse page_1.html")
        print("  python3 live_puppeteer_scraper.py --parse page_2.html")
        print("  etc.")
        print("\n" + "=" * 60)
