import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
from datetime import datetime
import os
import shutil
import re


@dataclass
class Feed:
    title: str
    xml_url: str
    html_url: str
    category: str = None


class OPMLParser:
    def __init__(self, opml_file: str):
        self.opml_file = opml_file
        self.feeds = []
        self.categories = {}
        
    def parse(self) -> Tuple[List[Feed], Dict[str, List[Feed]]]:
        tree = ET.parse(self.opml_file)
        root = tree.getroot()
        body = root.find('body')
        
        self._parse_outline(body, None)
        
        return self.feeds, self.categories
    
    def _parse_outline(self, outline, current_category=None):
        for child in outline:
            if child.get('type') == 'rss':
                feed = Feed(
                    title=child.get('title', ''),
                    xml_url=child.get('xmlUrl', ''),
                    html_url=child.get('htmlUrl', ''),
                    category=current_category
                )
                self.feeds.append(feed)
                
                if current_category:
                    if current_category not in self.categories:
                        self.categories[current_category] = []
                    self.categories[current_category].append(feed)
            else:
                category_name = child.get('text', '') or child.get('title', '')
                self._parse_outline(child, category_name)
    
    def get_categories(self) -> List[str]:
        return sorted(self.categories.keys())
    
    def get_feeds_by_category(self, category: str) -> List[Feed]:
        return self.categories.get(category, [])
    
    def remove_feeds(self, feeds_to_remove: Set[str], output_file: str = None):
        """Remove specified feeds from OPML and save to a new file."""
        tree = ET.parse(self.opml_file)
        root = tree.getroot()
        body = root.find('body')
        
        removed_count = 0
        
        def remove_from_outline(outline):
            nonlocal removed_count
            to_remove = []
            
            for child in outline:
                if child.get('type') == 'rss':
                    if child.get('title', '') in feeds_to_remove or child.get('xmlUrl', '') in feeds_to_remove:
                        to_remove.append(child)
                        removed_count += 1
                else:
                    remove_from_outline(child)
            
            for child in to_remove:
                outline.remove(child)
        
        remove_from_outline(body)
        
        # Save to file
        if output_file is None:
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = self.opml_file.replace('.xml', f'_cleaned_{timestamp}.xml')
        
        # Pretty print the XML
        ET.indent(tree, space='  ')
        tree.write(output_file, encoding='UTF-8', xml_declaration=True)
        
        return output_file, removed_count
    
    @staticmethod
    def manage_feed_files(source_file: str, target_name: str = "all_feeds.xml") -> str:
        """
        Manage feed files with proper naming and archiving.
        
        - If all_feeds.xml exists with timestamp, archive it
        - Copy source file to all_feeds_YYYYMMDD_HHMMSS.xml
        - Return the new filename
        """
        directory = os.path.dirname(source_file) or '.'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Pattern to match all_feeds_TIMESTAMP.xml
        pattern = re.compile(r'^all_feeds_(\d{8}_\d{6})\.xml$')
        
        # Find existing all_feeds file
        existing_all_feeds = None
        for file in os.listdir(directory):
            if pattern.match(file):
                existing_all_feeds = os.path.join(directory, file)
                break
        
        # Archive existing all_feeds if it exists
        if existing_all_feeds:
            # Extract timestamp from filename
            match = pattern.match(os.path.basename(existing_all_feeds))
            if match:
                old_timestamp = match.group(1)
                archive_name = os.path.join(directory, f'archived_feeds_{old_timestamp}.xml')
                shutil.move(existing_all_feeds, archive_name)
                print(f"Archived existing feed file to: {archive_name}")
        
        # Create new all_feeds file
        new_filename = os.path.join(directory, f'all_feeds_{timestamp}.xml')
        shutil.copy2(source_file, new_filename)
        print(f"Created new main feed file: {new_filename}")
        
        return new_filename
    
    @staticmethod
    def get_current_feeds_file(directory: str = '.') -> Optional[str]:
        """Find the current all_feeds_TIMESTAMP.xml file."""
        pattern = re.compile(r'^all_feeds_(\d{8}_\d{6})\.xml$')
        
        feed_files = []
        for file in os.listdir(directory):
            match = pattern.match(file)
            if match:
                timestamp = match.group(1)
                feed_files.append((timestamp, os.path.join(directory, file)))
        
        if feed_files:
            # Sort by timestamp and return the newest
            feed_files.sort(reverse=True)
            return feed_files[0][1]
        
        return None