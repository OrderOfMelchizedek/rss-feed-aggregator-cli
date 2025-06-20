#!/usr/bin/env python3

import click
from rich.console import Console
from rich.text import Text
from rich.prompt import Confirm
from datetime import datetime
import os
import re
from opml_parser import OPMLParser
from feed_parser import FeedParser
from typing import Optional, List
from difflib import get_close_matches
try:
    from gemini_summarizer import GeminiSummarizer
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


console = Console()


def find_opml_file():
    # First, look for all_feeds_TIMESTAMP.xml
    current_feeds = OPMLParser.get_current_feeds_file()
    if current_feeds:
        return current_feeds
    
    # Otherwise, look for any feed file
    for file in os.listdir('.'):
        if file.endswith('.xml') and 'feed' in file.lower():
            return file
    return None


def fuzzy_find_category(search_term: str, categories: List[str]) -> Optional[str]:
    """Find category using fuzzy matching."""
    if not search_term:
        return None
    
    search_lower = search_term.lower()
    
    # First, try exact match (case-insensitive)
    for cat in categories:
        if search_lower == cat.lower():
            return cat
    
    # Try partial matches - category contains search term
    matches = []
    for cat in categories:
        cat_lower = cat.lower()
        # Check if search term is in category name
        if search_lower in cat_lower:
            matches.append(cat)
        # Check if category starts with search term (for numbers like "05")
        elif cat_lower.startswith(search_lower):
            matches.append(cat)
        # Check if search term matches the part after the number prefix
        elif ' ' in cat and search_lower in cat_lower.split(' ', 1)[1]:
            matches.append(cat)
    
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        # If multiple matches, prefer exact word match
        for match in matches:
            words = match.lower().split()
            if search_lower in words:
                return match
        # Otherwise return the first match
        return matches[0]
    
    # Try fuzzy matching with difflib
    close_matches = get_close_matches(search_term, categories, n=1, cutoff=0.6)
    if close_matches:
        return close_matches[0]
    
    return None


def fuzzy_find_feed(search_term: str, feeds: List) -> List:
    """Find feeds using fuzzy matching."""
    if not search_term:
        return []
    
    search_lower = search_term.lower()
    matches = []
    
    # First try exact matches
    for feed in feeds:
        if search_lower == feed.title.lower():
            return [feed]
    
    # Then try partial matches
    for feed in feeds:
        if search_lower in feed.title.lower():
            matches.append(feed)
    
    if matches:
        return matches
    
    # Try fuzzy matching
    feed_titles = [f.title for f in feeds]
    close_matches = get_close_matches(search_term, feed_titles, n=5, cutoff=0.6)
    
    return [f for f in feeds if f.title in close_matches]


def get_article_counts_for_feeds(feeds, feed_parser):
    """Get article counts for a list of feeds using parallel fetching."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from rich.progress import Progress, SpinnerColumn, TextColumn
    
    counts = {}
    
    def count_feed_articles(feed):
        articles = feed_parser.fetch_feed(feed.xml_url, feed.title, feed.category)
        return feed.title, len(articles)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task(f"Counting articles in {len(feeds)} feeds...", total=len(feeds))
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_feed = {executor.submit(count_feed_articles, feed): feed for feed in feeds}
            
            for future in as_completed(future_to_feed):
                try:
                    feed_title, count = future.result()
                    counts[feed_title] = count
                except Exception as e:
                    feed = future_to_feed[future]
                    counts[feed.title] = 0
                progress.advance(task)
    
    return counts


def display_articles(articles, show_summary=True):
    if not articles:
        console.print("[yellow]No articles found in the last 24 hours.[/yellow]")
        return
    
    console.print(f"\n[bold]Found {len(articles)} articles from the last 24 hours[/bold]\n")
    
    for article in articles:
        time_str = article.published.strftime("%Y-%m-%d %H:%M")
        
        console.print(f"[dim]{time_str}[/dim] | [cyan]{article.category}[/cyan] | [green]{article.feed_title}[/green]")
        console.print(f"  [bold white]{article.title}[/bold white]")
        console.print(f"  [blue][link={article.link}]{article.link}[/link][/blue]")
        
        if show_summary and article.summary:
            console.print(f"  [dim]{article.summary}[/dim]")
        
        console.print()  # Empty line between articles


@click.command()
@click.option('--category', '-c', help='Filter by category name')
@click.option('--feed', '-f', help='Filter by specific feed name')
@click.option('--list-categories', is_flag=True, help='List all available categories')
@click.option('--list-feeds', is_flag=True, help='List all feeds (optionally filtered by category)')
@click.option('--show-counts', is_flag=True, help='Show article counts from past 24h when listing (slower but informative)')
@click.option('--health-check', is_flag=True, help='Check health of all feeds and identify problems')
@click.option('--remove-defunct', is_flag=True, help='Remove defunct feeds found during health check (creates new OPML file)')
@click.option('--fix-urls', is_flag=True, help='Automatically fix known URL issues in OPML file')
@click.option('--export-health', help='Export health check results to a file (CSV or JSON)')
@click.option('--organize-feeds', help='Organize feed file as all_feeds_TIMESTAMP.xml (provide source file)')
@click.option('--no-summary', is_flag=True, help='Hide article summaries')
@click.option('--summarize', is_flag=True, help='Generate AI summary of articles using Gemini')
@click.option('--opml', help='Path to OPML file (auto-detected if not specified)')
@click.option('--limit', '-l', type=int, help='Limit number of articles shown')
def main(category, feed, list_categories, list_feeds, show_counts, health_check, remove_defunct, fix_urls, export_health, organize_feeds, no_summary, summarize, opml, limit):
    """
    RSS Feed Aggregator - Fetch articles from the last 24 hours
    
    Examples:
        rss_reader                     # All articles from last 24 hours
        rss_reader -c "Tech Blogs"     # Articles from Tech Blogs category
        rss_reader -f "Hacker News"    # Articles from Hacker News feed
        rss_reader --list-categories   # Show all categories
    """
    
    # Handle feed organization first
    if organize_feeds:
        if not os.path.exists(organize_feeds):
            console.print(f"[red]Error: File '{organize_feeds}' not found.[/red]")
            return
        
        new_file = OPMLParser.manage_feed_files(organize_feeds)
        console.print(f"\n[green]✓ Feed file organized successfully![/green]")
        console.print(f"[dim]You can now use the RSS reader normally - it will automatically find {os.path.basename(new_file)}[/dim]")
        return
    
    opml_file = opml or find_opml_file()
    if not opml_file or not os.path.exists(opml_file):
        console.print("[red]Error: Could not find OPML file. Please specify with --opml option.[/red]")
        return
    
    parser = OPMLParser(opml_file)
    all_feeds, categories_dict = parser.parse()
    
    if list_categories:
        console.print("\n[bold]Available Categories:[/bold]\n")
        
        if show_counts:
            # Show categories with article counts
            feed_parser = FeedParser()
            
            console.print("[dim]Counting articles across all categories...[/dim]\n")
            
            # Get counts for all feeds in parallel
            all_feed_counts = get_article_counts_for_feeds(all_feeds, feed_parser)
            
            # Aggregate by category
            category_counts = {}
            for cat in parser.get_categories():
                cat_feeds = categories_dict.get(cat, [])
                total_articles = sum(all_feed_counts.get(feed.title, 0) for feed in cat_feeds)
                category_counts[cat] = (len(cat_feeds), total_articles)
            
            for cat in parser.get_categories():
                feed_count, article_count = category_counts[cat]
                if article_count > 0:
                    console.print(f"  • {cat} ({feed_count} feeds, [bold green]{article_count} articles[/bold green])")
                else:
                    console.print(f"  • {cat} ({feed_count} feeds, [dim]no articles[/dim])")
        else:
            # Show categories without counts (faster)
            for cat in parser.get_categories():
                feed_count = len(categories_dict.get(cat, []))
                console.print(f"  • {cat} ({feed_count} feeds)")
        return
    
    if list_feeds:
        if category:
            # Use fuzzy matching for category
            matched_category = fuzzy_find_category(category, parser.get_categories())
            if not matched_category:
                console.print(f"[red]Category '{category}' not found.[/red]")
                suggestions = get_close_matches(category, parser.get_categories(), n=3, cutoff=0.4)
                if suggestions:
                    console.print("[yellow]Did you mean one of these?[/yellow]")
                    for s in suggestions:
                        console.print(f"  • {s}")
                return
            feeds = parser.get_feeds_by_category(matched_category)
            console.print(f"\n[bold]Feeds in category '{matched_category}':[/bold]\n")
        else:
            feeds = all_feeds
            console.print(f"\n[bold]All Feeds ({len(feeds)} total):[/bold]\n")
        
        if show_counts:
            # Show feeds with article counts
            feed_parser = FeedParser()
            feed_counts = get_article_counts_for_feeds(feeds, feed_parser)
            
            for feed in feeds:
                cat_str = f" [{feed.category}]" if feed.category else ""
                article_count = feed_counts.get(feed.title, 0)
                if article_count > 0:
                    console.print(f"  • {feed.title}{cat_str} ([bold green]{article_count} articles[/bold green])")
                else:
                    console.print(f"  • {feed.title}{cat_str} ([dim]no articles[/dim])")
        else:
            # Show feeds without counts (faster)
            for feed in feeds:
                cat_str = f" [{feed.category}]" if feed.category else ""
                console.print(f"  • {feed.title}{cat_str}")
        return
    
    if health_check:
        console.print("\n[bold]Feed Health Check[/bold]\n")
        console.print("[dim]Checking all feeds for issues...[/dim]\n")
        
        feed_parser = FeedParser()
        problem_feeds = []
        healthy_feeds = []
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
        
        def check_feed(feed):
            is_healthy, error_msg, article_count, suggested_fix = feed_parser.check_feed_health(feed.xml_url, feed.title)
            return feed, is_healthy, error_msg, article_count, suggested_fix
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:
            task = progress.add_task(f"Checking {len(all_feeds)} feeds...", total=len(all_feeds))
            
            with ThreadPoolExecutor(max_workers=20) as executor:
                future_to_feed = {executor.submit(check_feed, feed): feed for feed in all_feeds}
                
                for future in as_completed(future_to_feed):
                    feed, is_healthy, error_msg, article_count, suggested_fix = future.result()
                    
                    if is_healthy:
                        healthy_feeds.append((feed, article_count))
                    else:
                        problem_feeds.append((feed, error_msg, suggested_fix))
                    
                    progress.advance(task)
        
        # Display results
        console.print(f"\n[bold green]Healthy feeds: {len(healthy_feeds)}[/bold green]")
        console.print(f"[bold red]Problem feeds: {len(problem_feeds)}[/bold red]\n")
        
        if problem_feeds:
            console.print("[bold]Problem Feeds:[/bold]\n")
            
            # Group by error type
            error_groups = {}
            fixable_feeds = []
            
            for feed, error, suggested_fix in problem_feeds:
                error_type = error.split(':')[0]
                if error_type not in error_groups:
                    error_groups[error_type] = []
                error_groups[error_type].append((feed, error, suggested_fix))
                
                if suggested_fix:
                    fixable_feeds.append((feed, suggested_fix))
            
            for error_type, feeds in sorted(error_groups.items()):
                console.print(f"\n[yellow]{error_type}:[/yellow] ({len(feeds)} feeds)")
                for feed, error, suggested_fix in feeds[:10]:  # Show first 10 of each type
                    console.print(f"  • {feed.title} [{feed.category}]")
                    console.print(f"    [dim]{feed.xml_url}[/dim]")
                    console.print(f"    [red]{error}[/red]")
                    if suggested_fix:
                        console.print(f"    [green]→ Suggested fix: {suggested_fix}[/green]")
                if len(feeds) > 10:
                    console.print(f"  [dim]... and {len(feeds) - 10} more[/dim]")
            
            if fixable_feeds:
                console.print(f"\n[bold yellow]Found {len(fixable_feeds)} feeds with suggested URL fixes[/bold yellow]")
                
                if fix_urls:
                    console.print(f"\n[bold]Applying URL fixes...[/bold]")
                    import xml.etree.ElementTree as ET
                    
                    # Create a mapping of old URLs to new URLs
                    url_fixes = {feed.xml_url: fix for feed, fix in fixable_feeds}
                    
                    # Parse and update OPML
                    tree = ET.parse(opml_file)
                    root = tree.getroot()
                    body = root.find('body')
                    
                    fixed_count = 0
                    
                    def fix_outline_urls(outline):
                        nonlocal fixed_count
                        for child in outline:
                            if child.get('type') == 'rss':
                                xml_url = child.get('xmlUrl', '')
                                if xml_url in url_fixes:
                                    child.set('xmlUrl', url_fixes[xml_url])
                                    fixed_count += 1
                                    console.print(f"  [green]✓[/green] Fixed: {child.get('title', 'Unknown')}")
                            else:
                                fix_outline_urls(child)
                    
                    fix_outline_urls(body)
                    
                    if fixed_count > 0:
                        # Save updated OPML to temporary file
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        temp_file = opml_file.replace('.xml', f'_temp_fixed_{timestamp}.xml')
                        ET.indent(tree, space='  ')
                        tree.write(temp_file, encoding='UTF-8', xml_declaration=True)
                        
                        # Use manage_feed_files to properly organize it
                        new_file = OPMLParser.manage_feed_files(temp_file)
                        os.remove(temp_file)  # Clean up temp file
                        
                        console.print(f"\n[green]✓ Fixed {fixed_count} feed URLs[/green]")
                        console.print(f"[green]✓ Updated feed file: {os.path.basename(new_file)}[/green]")
                        console.print(f"\n[dim]The RSS reader will now use this updated file automatically.[/dim]")
                    else:
                        console.print("[yellow]No URLs were fixed[/yellow]")
            
            if export_health:
                # Export health check results
                import json
                import csv
                
                export_data = []
                
                # Add healthy feeds
                for feed, article_count in healthy_feeds:
                    export_data.append({
                        'title': feed.title,
                        'url': feed.xml_url,
                        'category': feed.category or '',
                        'status': 'healthy',
                        'error': '',
                        'article_count': article_count,
                        'suggested_fix': ''
                    })
                
                # Add problem feeds
                for feed, error, suggested_fix in problem_feeds:
                    export_data.append({
                        'title': feed.title,
                        'url': feed.xml_url,
                        'category': feed.category or '',
                        'status': 'error',
                        'error': error,
                        'article_count': 0,
                        'suggested_fix': suggested_fix or ''
                    })
                
                if export_health.lower().endswith('.json'):
                    with open(export_health, 'w') as f:
                        json.dump(export_data, f, indent=2)
                    console.print(f"\n[green]✓ Health check results exported to: {export_health}[/green]")
                else:
                    # Default to CSV
                    csv_file = export_health if export_health.lower().endswith('.csv') else export_health + '.csv'
                    with open(csv_file, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=['title', 'url', 'category', 'status', 'error', 'article_count', 'suggested_fix'])
                        writer.writeheader()
                        writer.writerows(export_data)
                    console.print(f"\n[green]✓ Health check results exported to: {csv_file}[/green]")
            
            if remove_defunct:
                console.print(f"\n[bold yellow]Removing {len(problem_feeds)} defunct feeds...[/bold yellow]")
                
                feeds_to_remove = {feed.title for feed, _, _ in problem_feeds}
                temp_file, removed_count = parser.remove_feeds(feeds_to_remove)
                
                # Use manage_feed_files to properly organize it
                new_file = OPMLParser.manage_feed_files(temp_file)
                os.remove(temp_file)  # Clean up temp file
                
                console.print(f"[green]✓ Removed {removed_count} feeds[/green]")
                console.print(f"[green]✓ Updated feed file: {os.path.basename(new_file)}[/green]")
                console.print(f"\n[dim]The RSS reader will now use this updated file automatically.[/dim]")
        else:
            console.print("[green]All feeds are healthy![/green]")
        
        return
    
    feed_parser = FeedParser()
    
    feeds_to_fetch = []
    
    if feed:
        matched_feeds = fuzzy_find_feed(feed, all_feeds)
        if not matched_feeds:
            console.print(f"[red]Feed '{feed}' not found.[/red]")
            return
        feeds_to_fetch = [(f.xml_url, f.title, f.category) for f in matched_feeds]
        if len(matched_feeds) > 1:
            console.print(f"[yellow]Found {len(matched_feeds)} feeds matching '{feed}'[/yellow]")
    elif category:
        # Try fuzzy matching for category
        matched_category = fuzzy_find_category(category, parser.get_categories())
        if not matched_category:
            console.print(f"[red]Category '{category}' not found.[/red]")
            # Suggest similar categories
            suggestions = get_close_matches(category, parser.get_categories(), n=3, cutoff=0.4)
            if suggestions:
                console.print("[yellow]Did you mean one of these?[/yellow]")
                for s in suggestions:
                    console.print(f"  • {s}")
            return
        
        if matched_category != category:
            console.print(f"[green]Found category: {matched_category}[/green]")
        
        category_feeds = parser.get_feeds_by_category(matched_category)
        feeds_to_fetch = [(f.xml_url, f.title, f.category) for f in category_feeds]
    else:
        feeds_to_fetch = [(f.xml_url, f.title, f.category) for f in all_feeds]
    
    console.print(f"\n[bold]Fetching articles from {len(feeds_to_fetch)} feeds...[/bold]\n")
    
    articles = feed_parser.fetch_multiple_feeds(feeds_to_fetch)
    
    if limit:
        articles = articles[:limit]
    
    display_articles(articles, show_summary=not no_summary)
    
    if articles:
        console.print(f"\n[dim]Showing articles from {articles[-1].published.strftime('%Y-%m-%d %H:%M')} to {articles[0].published.strftime('%Y-%m-%d %H:%M')}[/dim]")
        
        # Handle AI summarization if requested
        if summarize:
            if not GEMINI_AVAILABLE:
                console.print("\n[red]Error: google-genai package not installed.[/red]")
                console.print("Install it with: pip install google-genai")
                return
                
            try:
                console.print("\n[bold]Generating AI Summary...[/bold]")
                
                summarizer = GeminiSummarizer()
                prepared_articles = summarizer.prepare_articles_for_summary(articles)
                
                # Display token count
                total_tokens = summarizer.display_token_summary(prepared_articles)
                
                console.print("\n[dim]Sending to Gemini API...[/dim]")
                summary = summarizer.summarize_articles(prepared_articles)
                
                if summary:
                    console.print("\n[bold green]AI Summary Generated:[/bold green]\n")
                    console.print(summary)
                    
                    # Automatically save summary to file
                    console.print("\n[dim]Generating title...[/dim]")
                    generated_title = summarizer.generate_title(summary)
                    
                    # Create filename with date and title
                    date_str = datetime.now().strftime('%Y-%m-%d')
                    # Sanitize title for filename
                    safe_title = re.sub(r'[^\w\s-]', '', generated_title)
                    safe_title = re.sub(r'[-\s]+', '-', safe_title)
                    filename = f"{date_str} {safe_title}.md"
                    
                    # Save to Obsidian folder
                    obsidian_folder = '/Users/svaug/Library/CloudStorage/Dropbox/Obsidian/Personal'
                    filepath = os.path.join(obsidian_folder, filename)
                    
                    # Ensure the directory exists
                    os.makedirs(obsidian_folder, exist_ok=True)
                    
                    with open(filepath, 'w') as f:
                        f.write(f"# {generated_title}\n\n")
                        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                        f.write(f"Generated from {len(articles)} articles\n")
                        f.write(f"Input tokens: {total_tokens:,}\n")
                        
                        # Calculate output tokens and costs
                        output_tokens = len(summary.split()) * 1.34  # Estimate output tokens
                        
                        # Get pricing based on model
                        if 'flash-lite' in summarizer.model_name.lower():
                            input_price = 0.10
                            output_price = 0.40
                            model_display = "Gemini 2.5 Flash-Lite"
                        elif 'flash' in summarizer.model_name.lower():
                            input_price = 0.30
                            output_price = 2.50
                            model_display = "Gemini 2.5 Flash"
                        else:
                            input_price = 1.25
                            output_price = 10.00
                            model_display = "Gemini 2.5 Pro"
                        
                        input_cost = (total_tokens / 1_000_000) * input_price
                        output_cost = (output_tokens / 1_000_000) * output_price
                        total_cost = input_cost + output_cost
                        
                        f.write(f"Output tokens: ~{int(output_tokens):,}\n")
                        f.write(f"Model: {model_display}\n")
                        f.write(f"Estimated cost: ${total_cost:.6f} (input: ${input_cost:.6f}, output: ${output_cost:.6f})\n")
                        f.write("\n---\n\n")
                        f.write(summary)
                        f.write("\n\n---\n\n")
                        f.write("## Appendix: Full Article List\n\n")
                        
                        # Append all articles with their details
                        for i, article in enumerate(articles, 1):
                            f.write(f"### {i}. {article.title}\n")
                            f.write(f"- **Source:** {article.feed_title}\n")
                            f.write(f"- **Category:** {article.category}\n")
                            f.write(f"- **Published:** {article.published.strftime('%Y-%m-%d %H:%M')}\n")
                            f.write(f"- **URL:** {article.link}\n")
                            if article.summary:
                                f.write(f"- **Summary:** {article.summary}\n")
                            f.write("\n")
                    
                    console.print(f"\n[green]✓ Summary automatically saved to: {filename}[/green]")
                    console.print(f"[dim]Full path: {filepath}[/dim]")
                
            except Exception as e:
                console.print(f"\n[red]Error during summarization: {str(e)}[/red]")
                # Print full traceback for debugging
                import traceback
                console.print("[dim]Full traceback:[/dim]")
                console.print(traceback.format_exc())


if __name__ == '__main__':
    main()