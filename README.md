# RSS Feed Aggregator CLI

A command-line tool to fetch and display articles from RSS feeds published in the last 24 hours.

## Features

- Parse OPML files containing RSS feed subscriptions
- Fetch articles from the last 24 hours
- Filter by category or specific feed with **fuzzy search**
- **Multiple sources**: Specify multiple categories and/or feeds in a single command
- Display articles with timestamps, categories, feed names, titles, and summaries
- Show article counts when listing categories or feeds
- **Health check** to identify defunct or problematic feeds
- Remove defunct feeds and create cleaned OPML file
- Export health check results to CSV or JSON
- **AI Summarization** using Google Gemini to create news digests
  - Combined summaries for all sources
  - Separate summaries for each category/feed with `--separate-summaries`
- Cache feeds to reduce network requests
- Parallel feed fetching for better performance

### Fuzzy Search

The tool includes intelligent fuzzy search for both categories and feeds:

- **Partial matches**: Type "higher education" to find "05 Higher Education"
- **Number prefixes**: Type "05" to find the category starting with that number
- **Misspellings**: Type "hgher educaton" and it will still find "05 Higher Education"
- **Suggestions**: If no match is found, the tool suggests similar categories

### Feed Health Check

The health check feature helps maintain your feed collection:

- **Identifies issues**: SSL errors, timeouts, 404 errors, parsing errors, etc.
- **Groups by error type**: See all feeds with similar problems together
- **Export results**: Save health check data as CSV or JSON for analysis
- **Auto-cleanup**: Remove all defunct feeds and create a cleaned OPML file
- **Detailed reporting**: Shows exact error messages for each problematic feed
- **URL auto-fixing**: Automatically updates known outdated URLs (e.g., BBC, Deutsche Welle)
- **Browser headers**: Uses browser-like headers to avoid 403 Forbidden errors

### Technical Improvements

To handle common feed issues, the tool now:

1. **Uses browser headers**: Mimics Chrome to avoid bot detection
2. **Fixes known URL migrations**: Automatically updates URLs that have moved
3. **Suggests fixes**: Shows URL replacements for SSL certificate errors
4. **Retries with fixes**: Attempts to fetch from corrected URLs automatically

### AI Summarization with Gemini

The tool can generate AI-powered summaries of your news articles:

- **Token Estimation**: Shows word count and estimated tokens (word count × 1.34)
- **Cost Estimation**: Provides approximate cost before making API calls
- **Custom Prompt**: Uses the prompt from `prompt_summarize.md` for consistent formatting
- **Two-Part Summary**:
  - Top 3 Most Important Developments
  - Thematic Summary of all other headlines
- **Automatic Save**: Summaries are automatically saved as markdown files with:
  - AI-generated title as filename
  - Full summary content
  - Appendix with complete article list including URLs and full summaries
  - Organized by date in folders: `/Obsidian/News/YYYY-MM-DD/`

#### Setup:
1. Install dependencies: `pip install -r requirements.txt`
2. Create a `.env` file with your Gemini API key and model preferences:
   ```
   GEMINI_API_KEY=your-api-key-here
   GEMINI_MODEL_SUMMARIES=gemini-2.5-flash
   GEMINI_MODEL_TITLES=gemini-2.5-flash-lite-preview-06-17
   ```
3. Create prompt files:
   - `prompt_summarize.md` - Instructions for article summarization
   - `prompt_generate-title.md` - Instructions for title generation

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Commands

```bash
# Fetch all articles from the last 24 hours
python rss_reader.py

# Filter by category (supports multiple)
python rss_reader.py --category "Tech Blogs"
python rss_reader.py -c "Higher Education"
python rss_reader.py -c "10 Reuters/AP" -c "10.1 Mainstream News"  # Multiple categories

# Filter by specific feed (supports multiple)
python rss_reader.py --feed "Hacker News"
python rss_reader.py -f "BBC News"
python rss_reader.py -f "BBC News" -f "CNN" -f "Reuters"  # Multiple feeds

# List all available categories
python rss_reader.py --list-categories

# List categories with article counts from past 24h
python rss_reader.py --list-categories --show-counts

# List all feeds
python rss_reader.py --list-feeds

# List feeds with article counts
python rss_reader.py --list-feeds --show-counts

# List feeds in specific categories with counts (supports multiple)
python rss_reader.py --list-feeds -c "Political News & Analysis" --show-counts
python rss_reader.py --list-feeds -c "Tech Blogs" -c "AI News" --show-counts

# Hide summaries (show only titles)
python rss_reader.py --no-summary

# Limit number of articles
python rss_reader.py --limit 50
python rss_reader.py -l 20 -c "Tech Blogs"

# Specify OPML file (auto-detected by default)
python rss_reader.py --opml "path/to/feeds.xml"

# Check health of all feeds
python rss_reader.py --health-check

# Check health and remove defunct feeds
python rss_reader.py --health-check --remove-defunct

# Check health and automatically fix known URL issues
python rss_reader.py --health-check --fix-urls

# Export health check results to CSV
python rss_reader.py --health-check --export-health feed_status.csv

# Export health check results to JSON
python rss_reader.py --health-check --export-health feed_status.json

# Combine: check, fix URLs, and export results
python rss_reader.py --health-check --fix-urls --export-health health.csv

# Generate AI summary of articles
python rss_reader.py --summarize                      # Summarize all articles
python rss_reader.py -c "Tech Blogs" --summarize      # Summarize specific category
python rss_reader.py --limit 50 --summarize           # Summarize top 50 articles

# Generate separate summaries for multiple sources
python rss_reader.py -c "Tech" -c "AI" --summarize --separate-summaries
python rss_reader.py -f "BBC" -f "CNN" --summarize --separate-summaries
```

### Examples

1. Get all tech-related articles (using fuzzy search):
```bash
python rss_reader.py -c "tech ai"  # Will find "80.1 Tech - Artifical Intelligence"
python rss_reader.py -c "80.1"     # Using just the number prefix
```

2. Get articles from mainstream news with limit:
```bash
python rss_reader.py -c "mainstream" -l 30  # Will find "10.1 Mainstream News"
```

3. Find feeds with fuzzy matching:
```bash
python rss_reader.py -f "hacker"    # Will find all feeds with "hacker" in the name
python rss_reader.py -f "simon"     # Will find "Simon Willison's Weblog"
```

4. Check what categories are available:
```bash
python rss_reader.py --list-categories
```

5. Combine multiple news sources and summarize:
```bash
# Get news from multiple categories with AI summary
python rss_reader.py -c "Reuters" -c "Mainstream" --summarize

# Generate separate summaries for each category
python rss_reader.py -c "Tech Blogs" -c "AI News" --summarize --separate-summaries

# Mix categories and specific feeds
python rss_reader.py -c "10 Reuters/AP" -f "BBC News" -f "CNN" --limit 50 --summarize
```

6. Monitor specific feeds:
```bash
# Get latest from your favorite feeds
python rss_reader.py -f "Hacker News" -f "Ars Technica" -f "The Verge"

# List feeds from multiple categories
python rss_reader.py --list-feeds -c "Tech" -c "AI" -c "Security" --show-counts
```

## How It Works

1. **OPML Parsing**: Reads your OPML file to extract RSS feed URLs and their categories
2. **Feed Fetching**: Downloads RSS feeds in parallel for better performance
3. **Date Filtering**: Shows only articles published in the last 24 hours
4. **Caching**: Caches feed data for 15 minutes to avoid excessive requests
5. **Display**: Formats output in a readable table with color coding

## Cache

The tool creates a `.cache` directory to store feed data. This cache expires after 15 minutes and helps reduce network requests when running the tool multiple times.

## Performance

With 600+ feeds, the initial fetch might take 30-60 seconds. Subsequent runs within 15 minutes will be much faster due to caching.