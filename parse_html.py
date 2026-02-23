#!/usr/bin/env python3
"""
Parse the HTML from jmail.world and extract email thread data
"""
import json
import re
import sys

def extract_threads_from_html(html_content):
    """
    Extract thread data from the Next.js HTML payload
    The data is embedded in script tags in a format like: self.__next_f.push([1,"..."])
    """
    threads = []
    
    # Look for the specific script content that contains thread data
    # The data appears in: "threads":[{...}]
    pattern = r'"threads":\s*(\[[\s\S]*?\})\s*\]'
    
    matches = re.findall(pattern, html_content)
    
    for match in matches:
        try:
            # The match is a JSON array string, but it's been escaped
            # Try to parse it as JSON
            threads_json = match + ']'  # Add closing bracket
            threads_data = json.loads(threads_json)
            threads.extend(threads_data)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            # The data might be double-escaped, try unescaping
            try:
                unescaped = match.replace('\\\\', '\\').replace('\\"', '"')
                threads_json = unescaped + ']'
                threads_data = json.loads(threads_json)
                threads.extend(threads_data)
            except:
                continue
    
    return threads

def main():
    # Read the HTML file passed as argument or from stdin
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            html_content = f.read()
    else:
        html_content = sys.stdin.read()
    
    # Extract threads
    threads = extract_threads_from_html(html_content)
    
    if threads:
        print(f"Extracted {len(threads)} email threads")
        # Save to JSON file
        with open('jmail_data/page_1_threads.json', 'w', encoding='utf-8') as f:
            json.dump(threads, f, indent=2, ensure_ascii=False)
        print("Saved to jmail_data/page_1_threads.json")
    else:
        print("No threads found in HTML")
        # Try to find where the data is
        if '"threads"' in html_content:
            print("Found 'threads' string in HTML, but couldn't extract it")
            # Show a sample
            idx = html_content.find('"threads"')
            print("Sample around 'threads':")
            print(html_content[max(0, idx-100):idx+500])

if __name__ == '__main__':
    main()
