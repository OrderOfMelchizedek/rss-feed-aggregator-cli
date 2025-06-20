import feedparser
import requests
from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from rich.progress import Progress, SpinnerColumn, TextColumn
import hashlib
import json
import os
from difflib import SequenceMatcher
from rich.console import Console


@dataclass
class Article:
    title: str
    summary: str
    link: str
    published: datetime
    feed_title: str
    category: Optional[str] = None


class FeedCache:
    def __init__(self, cache_dir: str = ".cache", cache_duration: int = 900):
        self.cache_dir = cache_dir
        self.cache_duration = cache_duration
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_path(self, url: str) -> str:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.json")
    
    def get(self, url: str) -> Optional[Dict]:
        cache_path = self._get_cache_path(url)
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
                cached_time = datetime.fromisoformat(cache_data['cached_at'])
                if datetime.now() - cached_time < timedelta(seconds=self.cache_duration):
                    return cache_data['data']
        return None
    
    def set(self, url: str, data: Dict):
        cache_path = self._get_cache_path(url)
        cache_data = {
            'cached_at': datetime.now().isoformat(),
            'data': data
        }
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)


class FeedParser:
    # Known URL replacements for feeds that have moved
    URL_REPLACEMENTS = {
        'newsrss.bbc.co.uk': 'feeds.bbci.co.uk',
        'www.physorg.com': 'phys.org',
        'rss.dw-world.de': 'rss.dw.com',
        'feeds.christianitytoday.com': 'www.christianitytoday.com/feeds',
    }
    
    def __init__(self, cache_duration: int = 900):
        self.cache = FeedCache(cache_duration=cache_duration)
        self.session = requests.Session()
        
        # Use a browser-like User-Agent to avoid 403 errors
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
    
    def _fix_url(self, url: str) -> str:
        """Apply known URL fixes for feeds that have moved."""
        for old_domain, new_domain in self.URL_REPLACEMENTS.items():
            if old_domain in url:
                fixed_url = url.replace(old_domain, new_domain)
                return fixed_url
        return url
    
    def check_feed_health(self, feed_url: str, feed_title: str) -> Tuple[bool, str, int, Optional[str]]:
        """Check if a feed is healthy and return status, error message, article count, and suggested fix."""
        try:
            # Skip non-HTTP URLs
            if not feed_url.startswith(('http://', 'https://')) or '@' in feed_url:
                return False, "Invalid URL format (not HTTP/HTTPS)", 0, None
            
            # Try the original URL first
            try:
                response = self.session.get(feed_url, timeout=10)
                response.raise_for_status()
            except (requests.exceptions.SSLError, requests.exceptions.HTTPError) as e:
                # Try with fixed URL if we have a known replacement
                fixed_url = self._fix_url(feed_url)
                if fixed_url != feed_url:
                    try:
                        response = self.session.get(fixed_url, timeout=10)
                        response.raise_for_status()
                        # Success with fixed URL!
                        return False, f"URL needs update: {feed_url} → {fixed_url}", 0, fixed_url
                    except:
                        # Fixed URL also failed, return original error
                        raise e
                else:
                    raise e
            
            feed_data = feedparser.parse(response.content)
            
            # Check for parsing errors
            if feed_data.get('bozo', False):
                error = str(feed_data.get('bozo_exception', 'Unknown parsing error'))
                return False, f"Feed parsing error: {error}", 0, None
            
            # Check if feed has entries
            if not feed_data.get('entries'):
                return False, "Feed has no entries", 0, None
            
            # Count recent articles
            now = datetime.now(timezone.utc)
            cutoff_time = now - timedelta(hours=24)
            recent_count = 0
            
            for entry in feed_data.entries:
                published = self._parse_date(entry)
                if published and published > cutoff_time:
                    recent_count += 1
            
            return True, "OK", recent_count, None
            
        except requests.exceptions.SSLError as e:
            # Check if URL fix might help
            fixed_url = self._fix_url(feed_url)
            if fixed_url != feed_url:
                return False, f"SSL Error (try: {fixed_url}): {str(e)}", 0, fixed_url
            return False, f"SSL Error: {str(e)}", 0, None
        except requests.exceptions.Timeout:
            return False, "Timeout - feed took too long to respond", 0, None
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection Error: {str(e)}", 0, None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                return False, f"HTTP Error 403: Forbidden (may be blocking bots)", 0, None
            return False, f"HTTP Error {e.response.status_code}: {e.response.reason}", 0, None
        except Exception as e:
            return False, f"Unexpected error: {str(e)}", 0, None
    
    def fetch_feed(self, feed_url: str, feed_title: str, category: Optional[str] = None) -> List[Article]:
        try:
            # Skip non-HTTP URLs (like keyword-monitoring feeds or email addresses)
            if not feed_url.startswith(('http://', 'https://')) or '@' in feed_url:
                return []
                
            cached_data = self.cache.get(feed_url)
            
            if cached_data:
                feed_data = feedparser.FeedParserDict(cached_data)
            else:
                try:
                    response = self.session.get(feed_url, timeout=10)
                    response.raise_for_status()
                except (requests.exceptions.SSLError, requests.exceptions.HTTPError) as e:
                    # Try with fixed URL if we have a known replacement
                    fixed_url = self._fix_url(feed_url)
                    if fixed_url != feed_url:
                        try:
                            response = self.session.get(fixed_url, timeout=10)
                            response.raise_for_status()
                            # Use the fixed URL for this request
                            feed_url = fixed_url
                        except:
                            # Fixed URL also failed, use original error
                            raise e
                    else:
                        raise e
                
                feed_data = feedparser.parse(response.content)
                # Only cache if parsing was successful
                if not feed_data.get('bozo', False):
                    self.cache.set(feed_url, dict(feed_data))
            
            articles = []
            now = datetime.now(timezone.utc)
            cutoff_time = now - timedelta(hours=24)
            
            for entry in feed_data.entries:
                published = self._parse_date(entry)
                if published and published > cutoff_time:
                    summary = self._extract_summary(entry)
                    article = Article(
                        title=entry.get('title', 'No title'),
                        summary=summary,
                        link=entry.get('link', ''),
                        published=published,
                        feed_title=feed_title,
                        category=category
                    )
                    articles.append(article)
            
            return articles
            
        except Exception as e:
            print(f"Error fetching {feed_title}: {str(e)}")
            return []
    
    def _parse_date(self, entry: Dict) -> Optional[datetime]:
        # Common timezone abbreviations to UTC offset mapping
        tzinfos = {
            'PST': -8 * 3600,
            'PDT': -7 * 3600,
            'MST': -7 * 3600,
            'MDT': -6 * 3600,
            'CST': -6 * 3600,
            'CDT': -5 * 3600,
            'EST': -5 * 3600,
            'EDT': -4 * 3600,
        }
        
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
        
        for field in date_fields:
            if hasattr(entry, field) and getattr(entry, field):
                try:
                    return datetime.fromtimestamp(time.mktime(getattr(entry, field)), tz=timezone.utc)
                except:
                    pass
        
        date_strings = ['published', 'updated', 'created', 'pubDate']
        for field in date_strings:
            if field in entry and entry[field]:
                try:
                    parsed_date = date_parser.parse(entry[field], tzinfos=tzinfos)
                    # If the parsed date is naive (no timezone), assume UTC
                    if parsed_date.tzinfo is None:
                        parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                    return parsed_date
                except:
                    pass
        
        return None
    
    def _extract_summary(self, entry: Dict) -> str:
        if 'summary' in entry:
            summary = entry['summary']
        elif 'description' in entry:
            summary = entry['description']
        elif 'content' in entry and len(entry['content']) > 0:
            summary = entry['content'][0].get('value', '')
        else:
            summary = ''
        
        # Strip HTML tags
        import re
        summary = re.sub('<[^<]+?>', '', summary)
        summary = summary.strip()
        
        if len(summary) > 300:
            summary = summary[:297] + '...'
        
        return summary
    
    def _deduplicate_articles(self, articles: List[Article], similarity_threshold: float = 0.85) -> List[Article]:
        """Remove duplicate articles based on title similarity and URL matching.
        Optimized version using hashing for better performance with large datasets."""
        if not articles:
            return articles
        
        console = Console()
        seen_urls = set()
        unique_articles = []
        duplicate_count = 0
        
        # First pass: Remove exact URL duplicates (O(n))
        for article in articles:
            if article.link in seen_urls:
                duplicate_count += 1
                continue
            seen_urls.add(article.link)
            unique_articles.append(article)
        
        # Second pass: Remove similar titles using a more efficient approach
        # Group articles by first few words to reduce comparisons
        title_groups = {}
        final_articles = []
        
        for article in unique_articles:
            # Create a normalized title for grouping
            title_words = article.title.lower().strip().split()[:3]  # First 3 words
            group_key = ' '.join(title_words)
            
            if group_key not in title_groups:
                title_groups[group_key] = []
            
            # Only compare with articles in the same group
            is_duplicate = False
            for existing in title_groups[group_key]:
                similarity = SequenceMatcher(None, 
                    article.title.lower().strip(), 
                    existing.title.lower().strip()
                ).ratio()
                
                if similarity >= similarity_threshold:
                    # Keep the one with more content
                    if len(article.summary) > len(existing.summary):
                        # Replace the existing article
                        final_articles.remove(existing)
                        title_groups[group_key].remove(existing)
                        title_groups[group_key].append(article)
                        final_articles.append(article)
                    else:
                        duplicate_count += 1
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                title_groups[group_key].append(article)
                final_articles.append(article)
        
        if duplicate_count > 0:
            console.print(f"[dim]Removed {duplicate_count} duplicate articles[/dim]")
        
        return final_articles
    
    def fetch_multiple_feeds(self, feeds: List[Tuple[str, str, Optional[str]]], max_workers: int = 20) -> List[Article]:
        all_articles = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task(f"Fetching {len(feeds)} feeds...", total=len(feeds))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_feed = {
                    executor.submit(self.fetch_feed, url, title, category): (url, title, category)
                    for url, title, category in feeds
                }
                
                for future in as_completed(future_to_feed):
                    articles = future.result()
                    all_articles.extend(articles)
                    progress.advance(task)
        
        # Deduplicate articles before sorting
        unique_articles = self._deduplicate_articles(all_articles)
        
        return sorted(unique_articles, key=lambda x: x.published, reverse=True)