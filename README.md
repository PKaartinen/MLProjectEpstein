# Jmail.world Email Scraper

A comprehensive Python script to scrape Jeffrey Epstein's emails from [jmail.world](https://jmail.world), creating a structured dataset of the email metadata and content.

## Overview

This scraper extracts email data from jmail.world, which presents government-released emails in a Gmail-like interface. The site uses Next.js with server-side rendering, embedding data directly in the HTML response.

### Site Structure Analysis

**Key Findings:**
- **Total Emails:** ~7,499 emails
- **Pagination:** 100 threads per page across 75 pages
- **Data Format:** JSON embedded in Next.js HTML payload
- **Architecture:** Server-side rendered React with Next.js

**Email Data Structure:**
Each email thread contains:
- `doc_id`: Unique document identifier
- `first_message_id`: First message in thread
- `subject`: Email subject line
- `sender_name`: Sender's name
- `sender_email`: Sender's email address
- `date`: Formatted date string
- `preview`: Email preview text
- `message_count`: Number of messages in thread
- `attachments`: Number of attachments
- `star_count`: Community star count
- `unredact_count`: Community unredaction count
- `email_drop_id`: Source batch identifier
- `is_from_epstein`: Boolean if from Epstein
- `is_redacted`: Boolean if contains redactions

## Installation

1. Clone or download this repository
2. Install Python 3.8 or higher
3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Examples

**Scrape first page only (test run):**
```bash
python jmail_scraper.py
```

**Scrape pages 1-5:**
```bash
python jmail_scraper.py --pages 1 5
```

**Scrape all 75 pages:**
```bash
python jmail_scraper.py --all
```

**Get site statistics:**
```bash
python jmail_scraper.py --stats
```

**Custom delay between requests (respectful scraping):**
```bash
python jmail_scraper.py --all --delay 3.0
```

**Output JSON only:**
```bash
python jmail_scraper.py --all --format json
```

**Custom output directory:**
```bash
python jmail_scraper.py --all --output-dir my_data
```

### Command-Line Options

```
usage: jmail_scraper.py [-h] [--pages START END] [--all] [--stats]
                        [--delay DELAY] [--output-dir OUTPUT_DIR]
                        [--format {json,csv,both}]

options:
  -h, --help            Show help message
  --pages START END     Scrape pages from START to END
  --all                 Scrape all pages (1-75)
  --stats               Get site statistics
  --delay DELAY         Delay between requests in seconds (default: 2.0)
  --output-dir DIR      Output directory for scraped data (default: jmail_data)
  --format FORMAT       Output format: json, csv, or both (default: both)
```

## Output Format

The scraper generates two types of files:

### 1. JSON Format
```json
[
  {
    "doc_id": "abc123",
    "first_message_id": "msg456",
    "subject": "Meeting tomorrow",
    "sender_name": "John Doe",
    "sender_email": "john@example.com",
    "date": "Jan 15, 2005",
    "preview": "Hi, let's meet tomorrow at...",
    "message_count": 3,
    "attachments": 0,
    "star_count": 12,
    "unredact_count": 0,
    "email_drop_id": "batch1",
    "is_from_epstein": false,
    "is_redacted": false
  }
]
```

### 2. CSV Format
Spreadsheet-compatible format with all fields as columns.

## Technical Implementation

### Extraction Strategy

The scraper uses a multi-step approach:

1. **HTTP Requests:** Makes GET requests to paginated URLs
2. **HTML Parsing:** Extracts embedded JSON from Next.js script tags
3. **Data Extraction:** Parses JSON payloads containing thread metadata
4. **Rate Limiting:** Implements respectful delays between requests
5. **Incremental Saving:** Saves progress after each page

### Key Features

- ✅ **Respectful Scraping:** Built-in delays (default 2s between requests)
- ✅ **Incremental Progress:** Saves data after each page
- ✅ **Error Handling:** Robust error recovery and logging
- ✅ **Multiple Formats:** Outputs both JSON and CSV
- ✅ **Resume Capability:** Can start from any page
- ✅ **Detailed Logging:** Real-time progress tracking

## Data Extraction Method

The site embeds data using Next.js's server-side rendering:

```javascript
// Embedded in HTML as:
self.__next_f.push([1,"...escaped JSON..."])
```

The scraper:
1. Fetches raw HTML
2. Extracts script tag content using regex
3. Unescapes Unicode strings
4. Parses JSON payloads
5. Extracts thread arrays

## Performance

- **Speed:** ~2-3 seconds per page (with respectful delay)
- **Total Time:** ~3-4 minutes for all 75 pages
- **Memory:** Minimal (incremental processing)
- **Network:** ~1-2MB per page

## Ethics & Legal Considerations

**Important Notes:**
- This data is already public (government release)
- The site appears to be designed for public access
- Implement respectful rate limiting (don't overload the server)
- Check robots.txt and terms of service before large-scale scraping
- Consider reaching out to site administrators for bulk access

## Troubleshooting

### Common Issues

**No data extracted:**
- Site structure may have changed
- Check if site is accessible
- Verify internet connection

**Rate limiting errors:**
- Increase `--delay` parameter
- Check if IP is blocked (wait and retry)

**Incomplete data:**
- Script saves incremental progress
- Can resume from last successful page
- Check logs for specific errors

## Advanced Usage

### Scraping Thread Details

The current script extracts thread metadata. To get full email content:

```python
# Example extension
scraper = JmailScraper()
threads = scraper.scrape_all_pages(1, 5)

for thread in threads:
    detail = scraper.scrape_thread_detail(thread['doc_id'])
    # Process full email content
```

### Custom Data Processing

```python
from jmail_scraper import JmailScraper
import pandas as pd

# Scrape data
scraper = JmailScraper()
threads = scraper.scrape_all_pages(1, 10)

# Convert to pandas DataFrame
df = pd.DataFrame(threads)

# Analyze
epstein_emails = df[df['is_from_epstein'] == True]
print(f"Emails from Epstein: {len(epstein_emails)}")
```

## Future Enhancements

Potential improvements:
- [ ] Extract full email body text (requires clicking into threads)
- [ ] Download attachments
- [ ] Parallel processing for faster scraping
- [ ] Database storage (SQLite/PostgreSQL)
- [ ] Full-text search indexing
- [ ] Sentiment analysis
- [ ] Network graph of email relationships

## Project Structure

```
.
├── jmail_scraper.py      # Main scraper script
├── requirements.txt      # Python dependencies
├── README.md            # This file
└── jmail_data/          # Output directory (created automatically)
    ├── jmail_emails_20260217_120000.json
    ├── jmail_emails_20260217_120000.csv
    └── threads_page_1_to_75.json
```

## Contributing

Improvements welcome! Areas for contribution:
- Full email content extraction
- Better HTML parsing for thread details
- Alternative data formats (Parquet, SQLite)
- Data validation and deduplication
- Visualization tools

## License

MIT License - Feel free to use and modify

## Acknowledgments

- Data source: [jmail.world](https://jmail.world)
- Built with: Python, Requests, BeautifulSoup4
