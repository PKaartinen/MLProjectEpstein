#!/usr/bin/env python3
"""
Extract thread data from jmail.world HTML
Parses Next.js RSC (React Server Components) format
"""

import re
import json
from pathlib import Path

def extract_threads_from_html(html_content):
    """Extract threads from Next.js self.__next_f.push format"""
    
    # Find all self.__next_f.push calls
    pattern = r'self\.__next_f\.push\(\[(.*?)\]\)'
    matches = re.findall(pattern, html_content, re.DOTALL)
    
    print(f'Found {len(matches)} __next_f.push calls')
    
    threads = []
    
    for i, match in enumerate(matches):
        if '"threads":' in match and 'doc_id' in match:
            print(f'\nProcessing match {i} (contains thread data)')
            
            # Extract the JSON part
            # Format: 1,"escaped_json_string"
            parts = match.split(',', 1)
            if len(parts) < 2:
                continue
            
            json_str = parts[1].strip()
            
            # Remove surrounding quotes
            if json_str.startswith('"') and json_str.endswith('"'):
                json_str = json_str[1:-1]
            
            # Unescape - handle multiple levels of escaping
            # \\\\" -> \\"  -> "
            json_str = json_str.replace('\\\\"', '"').replace('\\\\', '\\')
            
            # Now find the threads array within this string
            threads_pattern = r'"threads":\s*(\[[^\]]+\])'
            threads_match = re.search(threads_pattern, json_str, re.DOTALL)
            
            if threads_match:
                threads_json_str = threads_match.group(1)
                
                # Fix common escaping issues
                threads_json_str = threads_json_str.replace('\\u003c', '<').replace('\\u003e', '>')
                threads_json_str = threads_json_str.replace('\\u0026', '&')
                
                try:
                    # Parse the threads array
                    threads_data = json.loads(threads_json_str)
                    threads.extend(threads_data)
                    print(f'✓ Extracted {len(threads_data)} threads')
                    break  # Usually only one match contains all threads
                except json.JSONDecodeError as e:
                    print(f'✗ JSON decode error: {e}')
                    # Save problematic JSON for debugging
                    with open('jmail_data/debug_json.txt', 'w') as f:
                        f.write(threads_json_str[:2000])
                    print('Saved debug JSON to jmail_data/debug_json.txt')
    
    return threads

def main():
    # Read the HTML file
    html_file = Path('jmail_data/raw_html.html')
    
    if not html_file.exists():
        print(f'Error: {html_file} not found')
        print('Run the HTTP fetch first to download the HTML')
        return
    
    print(f'Reading {html_file}')
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    print(f'HTML size: {len(html_content):,} characters\n')
    
    # Extract threads
    threads = extract_threads_from_html(html_content)
    
    if threads:
        print(f'\n{"="*60}')
        print(f'SUCCESS: Extracted {len(threads)} threads')
        print(f'{"="*60}\n')
        
        # Save to JSON
        output_file = Path('jmail_data/threads_page_1.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(threads, f, indent=2, ensure_ascii=False)
        
        print(f'✓ Saved to {output_file}')
        
        # Display sample thread
        if threads:
            print('\n=== Sample Thread ===')
            sample = threads[0]
            for key in ['doc_id', 'subject', 'latest_sender_name', 'latest_sender_email', 
                       'formatted_date', 'preview', 'starCount', 'unredactCount']:
                value = sample.get(key, 'N/A')
                print(f'{key:20s}: {value}')
        
        # Statistics
        print(f'\n=== Statistics ===')
        print(f'Total threads: {len(threads)}')
        redacted = sum(1 for t in threads if t.get('isRedacted'))
        print(f'Redacted emails: {redacted}')
        print(f'Unredacted emails: {len(threads) - redacted}')
        
        # Top starred threads
        top_starred = sorted(threads, key=lambda t: t.get('starCount', 0), reverse=True)[:3]
        print(f'\n=== Top 3 Starred Threads ===')
        for i, thread in enumerate(top_starred, 1):
            print(f"{i}. {thread.get('subject', 'No subject')[:50]} - {thread.get('starCount', 0)} stars")
        
        return threads
    else:
        print('\n✗ No threads extracted')
        return None

if __name__ == '__main__':
    main()
