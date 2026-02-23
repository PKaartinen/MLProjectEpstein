#!/usr/bin/env python3
"""
Extract thread data from jmail.world HTML
Handles Next.js RSC (React Server Components) escaped JSON format
"""

import re
import json
from pathlib import Path

def unescape_json_string(escaped_str):
    """Unescape a heavily escaped JSON string from Next.js RSC"""
    # Remove outer quotes if present
    if escaped_str.startswith('"') and escaped_str.endswith('"'):
        escaped_str = escaped_str[1:-1]
    
    # Unescape in stages
    # \\\\" -> \\" -> "
    result = escaped_str
    result = result.replace('\\\\"', '"')
    result = result.replace('\\\\', '\\')
    result = result.replace('\\u003c', '<')
    result = result.replace('\\u003e', '>')
    result = result.replace('\\u0026', '&')
    
    return result

def extract_threads_from_rsc_chunk(chunk_str):
    """Extract threads from a single RSC chunk"""
    # Unescape the chunk
    unescaped = unescape_json_string(chunk_str)
    
    # Find the threads array
    # Pattern: "threads":[{...},{...}]
    # Use a more lenient pattern that handles nested structures
    threads_start = unescaped.find('"threads":[')
    if threads_start == -1:
        return None
    
    # Find the end of the threads array
    # Start after "threads":[
    search_start = threads_start + len('"threads":[')
    
    # Count brackets to find matching ]
    bracket_count = 1
    pos = search_start
    in_string = False
    escape_next = False
    
    while pos < len(unescaped) and bracket_count > 0:
        char = unescaped[pos]
        
        if escape_next:
            escape_next = False
            pos += 1
            continue
        
        if char == '\\':
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
        # Extract the threads JSON (including the brackets)
        threads_json = unescaped[threads_start + len('"threads":'):pos]
        
        try:
            threads_data = json.loads(threads_json)
            return threads_data
        except json.JSONDecodeError as e:
            print(f'JSON decode error: {e}')
            # Save for debugging
            with open('jmail_data/debug_threads.json', 'w') as f:
                f.write(threads_json[:5000])
            print('Saved debug output to jmail_data/debug_threads.json')
            return None
    
    return None

def extract_threads_from_html(html_content):
    """Extract threads from Next.js self.__next_f.push format"""
    
    # Find all self.__next_f.push calls
    pattern = r'self\.__next_f\.push\(\[(.*?)\]\)'
    matches = re.findall(pattern, html_content, re.DOTALL)
    
    print(f'Found {len(matches)} __next_f.push calls')
    
    for i, match in enumerate(matches):
        # Check for escaped version (\\"threads\\":) since we're searching the raw match string before unescaping
        if ('\\' in match and 'threads' in match and 'doc_id' in match):
            print(f'\nProcessing match {i} (contains thread data)')
            print(f'Length: {len(match):,} characters')
            
            # Extract the JSON part (after the chunk ID)
            # Format: 1,"17:[...json...]"
            parts = match.split(',', 1)
            if len(parts) < 2:
                print('Could not split chunk into parts')
                continue
            
            chunk_json = parts[1].strip()
            threads = extract_threads_from_rsc_chunk(chunk_json)
            
            if threads:
                print(f'✓ Successfully extracted {len(threads)} threads')
                return threads
            else:
                print('✗ Failed to extract threads from this chunk')
    
    return []

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
                # Truncate long values
                if isinstance(value, str) and len(value) > 80:
                    value = value[:77] + '...'
                print(f'{key:20s}: {value}')
        
        # Statistics
        print(f'\n=== Statistics ===')
        print(f'Total threads: {len(threads)}')
        redacted = sum(1 for t in threads if t.get('isRedacted'))
        print(f'Redacted emails: {redacted}')
        print(f'Unredacted emails: {len(threads) - redacted}')
        
        # Count by email source
        sources = {}
        for t in threads:
            source = t.get('email_drop_id', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        print(f'\nThreads by source:')
        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            print(f'  {source}: {count}')
        
        # Top starred threads
        top_starred = sorted(threads, key=lambda t: t.get('starCount', 0), reverse=True)[:5]
        print(f'\n=== Top 5 Starred Threads ===')
        for i, thread in enumerate(top_starred, 1):
            subj = thread.get('subject', 'No subject')
            if len(subj) > 60:
                subj = subj[:57] + '...'
            print(f"{i}. {subj} - ⭐{thread.get('starCount', 0)}")
        
        return threads
    else:
        print('\n✗ No threads extracted')
        return None

if __name__ == '__main__':
    main()
