# Waters Knowledge Base Loader

A production-quality local Python application that extracts authorized Waters Knowledge Base articles, cleans and validates the extracted data, identifies associated instrument names, and loads the resulting records into an existing Supabase PostgreSQL database.

## Table of Contents

1. [Project Purpose](#project-purpose)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Output Files](#output-files)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)
9. [Security & Authorization](#security--authorization)
10. [Customization](#customization)

---

## Project Purpose

This application:

- Discovers authorized Waters Knowledge Base article URLs via sitemap or listing pages
- Downloads each article while respecting robots.txt, rate limits, and access permissions
- Extracts article number, title, URL, content, date, and instrument names
- Cleans, normalizes, and validates all extracted data
- Inserts new records and updates changed records in Supabase PostgreSQL
- Creates and reuses canonical instrument records
- Maintains article-to-instrument relationships
- Produces clear run summaries and error reports
- Supports safe restart and incremental synchronization

---

## Prerequisites

- **Python 3.11 or later**
- **pip** (Python package manager)
- **A Supabase project** with the required database schema already created
- **Network access** to the Waters Knowledge Base website

---

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd waters_knowledge_base_loader
```

### 2. Create a Virtual Environment

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows PowerShell:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

### 1. Create the .env File

Copy the example environment file:

**Linux/macOS:**
```bash
cp .env.example .env
```

**Windows PowerShell:**
```powershell
Copy-Item .env.example .env
```

### 2. Edit the .env File

Open `.env` and set your values:

```env
DATABASE_CONNECTION_URL=postgresql://postgres.user:password@host:5432/postgres
WATERS_KNOWLEDGE_BASE_START_URL=https://www.waters.com/nextgen/us/en/support/knowledge-base.html
WATERS_KNOWLEDGE_BASE_SITEMAP_URL=https://www.waters.com/sitemap.xml
CRAWL_DELAY_SECONDS=2.0
MAXIMUM_CONCURRENT_REQUESTS=2
LOG_LEVEL=INFO
RESPECT_ROBOTS_TXT=true
```

> **Important:** Never commit your `.env` file. It is excluded by `.gitignore`.

### 3. Test the Database Connection

```bash
python -c "
from dotenv import load_dotenv
load_dotenv()
from waters_knowledge_base.database.connection import DatabaseConnectionManager
manager = DatabaseConnectionManager()
manager.test_connection()
print('Connection successful!')
"
```

---

## Usage

### Process One Authorized Article

```bash
python run_extraction.py --article-url "https://www.waters.com/nextgen/us/en/support/knowledge-base/WKB12345.html"
```

### Dry Run (No Database Writes)

Test extraction and validation without writing to the database:

```bash
python run_extraction.py --mode full --maximum-articles 10 --dry-run
```

### 10-Article Test (With Database Writes)

```bash
python run_extraction.py --mode full --maximum-articles 10
```

### Full Authorized Extraction

```bash
python run_extraction.py --mode full
```

### Incremental Synchronization

Skip articles that haven't changed since the last run:

```bash
python run_extraction.py --mode incremental
```

### Discovery Only (No Downloads)

Find article URLs without downloading or processing them:

```bash
python run_extraction.py --mode discover-only
```

### Retry Failed Articles

```bash
python run_extraction.py --retry-failed output/failed_articles.json
```

### Debug Logging

```bash
python run_extraction.py --mode incremental --log-level DEBUG
```

### View All CLI Options

```bash
python run_extraction.py --help
```

---

## Output Files

All output files are generated in the `output/` directory:

| File | Description |
|------|-------------|
| `extraction_YYYY-MM-DD_HHMMSS.log` | Timestamped log file for each run |
| `extraction_summary.json` | Summary statistics (inserted, updated, unchanged, failed counts) |
| `failed_articles.json` | Details of failed articles with error information |
| `unreviewed_instrument_names.json` | Instrument names not found in the alias configuration |
| `discovered_article_urls.json` | All article URLs discovered during the run |

---

## Testing

### Run All Tests

```bash
pytest -v
```

### Run Specific Test Files

```bash
pytest tests/test_article_parser.py -v
pytest tests/test_content_cleaner.py -v
pytest tests/test_instrument_normalizer.py -v
pytest tests/test_article_validation.py -v
pytest tests/test_database_repositories.py -v
```

> **Note:** Database tests use mocks and do not require a live database connection.

---

## Troubleshooting

### "DATABASE_CONNECTION_URL is not set"
Copy `.env.example` to `.env` and set your Supabase PostgreSQL connection string.

### "RESPECT_ROBOTS_TXT must be 'true'"
This application requires robots.txt compliance. Ensure `RESPECT_ROBOTS_TXT=true` in your `.env`.

### Connection Timeout
- Check your Supabase project is running
- Verify the connection URL includes the correct host, port, and database
- If using Supabase connection pooler, ensure the pooler URL is correct

### No Articles Found
- The sitemap URL may not contain knowledge base articles
- Check `output/discovered_article_urls.json` to see what was found
- Article URL patterns in `text_helpers.py::is_article_url()` may need adjustment

### Extraction Returns Empty Content
- Page selectors in `article_parser.py` may need adjustment for the current site structure
- Use `--dry-run` to test extraction without database writes
- Check extraction warnings in the log file

---

## Security & Authorization

- This application **respects robots.txt** and will refuse to run if `RESPECT_ROBOTS_TXT=false`
- **No credentials** are logged or printed
- Connection URLs are **masked** in error messages
- **No proxy rotation**, user-agent rotation, CAPTCHA bypass, or stealth plugins are used
- Crawling uses **conservative rate limits** (2-second delay, 2 concurrent requests)
- Only authorized, publicly accessible articles are processed

---

## Customization

### Updating the Instrument Alias File

Edit `configuration/instrument_aliases.json` to add new instrument name mappings:

```json
{
  "new instrument name": "Canonical Name",
  "alternate spelling": "Canonical Name"
}
```

Keys are case-insensitive. Run the extraction again to apply new aliases. Previously unreviewed names will be resolved if a matching alias is added.

### Adjusting Page Selectors

If the Waters Knowledge Base website structure changes, you may need to update selectors:

1. **Article number selectors**: `extraction/article_parser.py` → `ARTICLE_NUMBER_SELECTORS`
2. **Title selectors**: `extraction/article_parser.py` → `TITLE_SELECTORS`
3. **Date selectors**: `extraction/article_parser.py` → `DATE_SELECTORS`
4. **Instrument heading labels**: `extraction/instrument_extractor.py` → `INSTRUMENT_SECTION_HEADING_LABELS`
5. **Boilerplate removal selectors**: `extraction/content_cleaner.py` → `BOILERPLATE_CSS_SELECTORS`
6. **Article URL patterns**: `utilities/text_helpers.py` → `is_article_url()`

Use `--dry-run` mode to test selector changes before committing to database writes.

### Optional: Content Hash Column Migration

The application currently compares article values in Python for change detection. To add a `content_hash` column to the database for more efficient comparison:

```sql
-- Optional migration (apply manually if approved)
ALTER TABLE public.articles ADD COLUMN content_hash varchar;
CREATE INDEX idx_articles_content_hash ON public.articles (content_hash);
```

This migration is optional and the application works without it.

---

## Project Structure

```
waters_knowledge_base_loader/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── scrapy.cfg
├── run_extraction.py              # CLI entry point
├── waters_knowledge_base/
│   ├── __init__.py
│   ├── settings.py                # Scrapy settings
│   ├── items.py                   # Scrapy items
│   ├── pipelines.py               # Processing pipeline
│   ├── middlewares.py              # Rate limiting middleware
│   ├── database/
│   │   ├── connection.py           # PostgreSQL connection manager
│   │   ├── article_repository.py   # Article CRUD operations
│   │   └── instrument_repository.py # Instrument & relationship ops
│   ├── extraction/
│   │   ├── article_parser.py       # HTML article extraction
│   │   ├── content_cleaner.py      # Boilerplate removal
│   │   ├── instrument_extractor.py # Instrument name extraction
│   │   └── instrument_normalizer.py # Alias resolution
│   ├── models/
│   │   └── article_record.py      # Pydantic validation model
│   ├── spiders/
│   │   └── waters_articles_spider.py # Scrapy spider
│   └── utilities/
│       ├── content_hashing.py      # SHA-256 change detection
│       ├── date_parsing.py         # Date format parsing
│       ├── run_reporting.py        # Summary & failure reports
│       └── text_helpers.py         # URL & text utilities
├── configuration/
│   └── instrument_aliases.json    # Instrument name aliases
├── output/
│   └── .gitkeep
└── tests/
    ├── fixtures/
    │   └── sample_article.html    # Test HTML fixture
    ├── test_article_parser.py
    ├── test_content_cleaner.py
    ├── test_instrument_normalizer.py
    ├── test_article_validation.py
    └── test_database_repositories.py
```
