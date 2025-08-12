import os
import re
import json
import logging
import hashlib
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse, unquote
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime

class BookmarksImporter:
    """
    A class for importing bookmarks from various formats including:
    - HTML bookmarks files (Netscape format)
    - JSON files
    - CSV files
    - Pocket exports
    """
    
    def __init__(self, bookmarks_dir: str = None):
        self.bookmarks_dir = bookmarks_dir or os.environ.get('BOOKMARKS_DIR', '/data/bookmarks')
        self.logger = logging.getLogger(__name__)
        
        # Ensure bookmarks directory exists
        os.makedirs(self.bookmarks_dir, exist_ok=True)
    
    def slugify(self, text: str) -> str:
        """Convert text to a URL-friendly slug"""
        if not text:
            return ""
        
        # Convert to lowercase and replace spaces with hyphens
        text = text.lower().strip()
        # Remove special characters, keep only alphanumeric and hyphens
        text = re.sub(r'[^a-z0-9\-]', '-', text)
        # Remove multiple consecutive hyphens
        text = re.sub(r'-+', '-', text)
        # Remove leading and trailing hyphens
        text = text.strip('-')
        
        return text
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file creation"""
        # Remove or replace unsafe characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    def create_bookmark_file(self, title: str, uri: str, category: str = "unsorted", 
                           tags: str = "", add_date: str = "", last_modified: str = "") -> Dict[str, Any]:
        """Create a bookmark file with the given metadata"""
        try:
            # Sanitize inputs
            title = title.strip() if title else "Untitled"
            uri = uri.strip() if uri else ""
            category = category.strip() if category else "unsorted"
            tags = tags.strip() if tags else ""
            
            # Create category directory
            category_dir = os.path.join(self.bookmarks_dir, self.slugify(category))
            os.makedirs(category_dir, exist_ok=True)
            
            # Generate filename
            safe_title = self.sanitize_filename(title)
            filename = f"{self.slugify(safe_title)}.md"
            filepath = os.path.join(category_dir, filename)
            
            # Check if file already exists
            if os.path.exists(filepath):
                # Add timestamp to make it unique
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{self.slugify(safe_title)}_{timestamp}.md"
                filepath = os.path.join(category_dir, filename)
            
            # Create markdown content
            content = f"""---
title: {title}
uri: {uri}
tags: [{tags}]
"""
            
            if add_date:
                content += f"add_date: {add_date}\n"
            if last_modified:
                content += f"last_modified: {last_modified}\n"
            
            content += f"""---
[{title}]({uri})
"""
            
            # Write file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"Created bookmark: {filepath}")
            
            return {
                "success": True,
                "filename": filepath,
                "title": title,
                "uri": uri,
                "category": category,
                "tags": tags
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create bookmark: {e}")
            return {
                "success": False,
                "error": str(e),
                "title": title,
                "uri": uri
            }
    
    def import_html_bookmarks(self, file_path: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Import bookmarks from HTML file (Netscape format)
        Supports folder structure and bookmark metadata
        """
        results = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "errors": [],
            "imported": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse HTML content
            bookmarks = self._parse_html_bookmarks(content)
            
            results["total"] = len(bookmarks)
            
            for bookmark in bookmarks:
                if dry_run:
                    results["imported"].append(bookmark)
                    results["success"] += 1
                else:
                    result = self.create_bookmark_file(
                        title=bookmark.get("title", ""),
                        uri=bookmark.get("uri", ""),
                        category=bookmark.get("category", "unsorted"),
                        tags=bookmark.get("tags", ""),
                        add_date=bookmark.get("add_date", ""),
                        last_modified=bookmark.get("last_modified", "")
                    )
                    
                    if result["success"]:
                        results["success"] += 1
                        results["imported"].append(result)
                    else:
                        results["failed"] += 1
                        results["errors"].append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to import HTML bookmarks: {e}")
            return {
                "total": 0,
                "success": 0,
                "failed": 1,
                "errors": [{"error": str(e)}],
                "imported": []
            }
    
    def _parse_html_bookmarks(self, html_content: str) -> List[Dict[str, str]]:
        """Parse HTML bookmarks content and extract bookmarks with folder structure"""
        bookmarks = []
        path_parts = []
        current_category = "unsorted"
        
        # Split content into lines for processing
        lines = html_content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Check for folder (H3 tag)
            folder_match = re.search(r'<dt><h3[^>]*>([^<]+)</h3>', line, re.IGNORECASE)
            if folder_match:
                folder_name = folder_match.group(1).strip()
                folder_slug = self.slugify(folder_name)
                path_parts.append(folder_slug)
                current_category = "/".join(path_parts)
                self.logger.debug(f"Found folder: {folder_name} -> {current_category}")
                continue
            
            # Check for bookmark (A tag)
            bookmark_match = re.search(r'<dt><a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', line, re.IGNORECASE)
            if bookmark_match:
                uri = unquote(bookmark_match.group(1).strip())
                title = bookmark_match.group(2).strip()
                
                # Extract additional attributes
                add_date = ""
                last_modified = ""
                tags = ""
                
                add_date_match = re.search(r'add_date="([^"]*)"', line)
                if add_date_match:
                    add_date = add_date_match.group(1)
                
                last_modified_match = re.search(r'last_modified="([^"]*)"', line)
                if last_modified_match:
                    last_modified = last_modified_match.group(1)
                
                tags_match = re.search(r'tags="([^"]*)"', line)
                if tags_match:
                    tags = tags_match.group(1)
                
                bookmark = {
                    "title": title,
                    "uri": uri,
                    "category": current_category,
                    "tags": tags,
                    "add_date": add_date,
                    "last_modified": last_modified
                }
                
                bookmarks.append(bookmark)
                self.logger.debug(f"Found bookmark: {title} -> {uri}")
                continue
            
            # Check for closing folder (</dl>)
            if re.search(r'</dl>', line, re.IGNORECASE):
                if path_parts:
                    path_parts.pop()
                    current_category = "/".join(path_parts) if path_parts else "unsorted"
                    self.logger.debug(f"Closed folder, current category: {current_category}")
        
        return bookmarks
    
    def import_json_bookmarks(self, file_path: str, dry_run: bool = False) -> Dict[str, Any]:
        """Import bookmarks from JSON file"""
        results = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "errors": [],
            "imported": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different JSON formats
            bookmarks = []
            if isinstance(data, list):
                bookmarks = data
            elif isinstance(data, dict):
                if "bookmarks" in data:
                    bookmarks = data["bookmarks"]
                elif "items" in data:
                    bookmarks = data["items"]
                else:
                    # Assume it's a single bookmark
                    bookmarks = [data]
            
            results["total"] = len(bookmarks)
            
            for bookmark in bookmarks:
                if dry_run:
                    results["imported"].append(bookmark)
                    results["success"] += 1
                else:
                    result = self.create_bookmark_file(
                        title=bookmark.get("title", bookmark.get("name", "")),
                        uri=bookmark.get("uri", bookmark.get("url", bookmark.get("link", ""))),
                        category=bookmark.get("category", bookmark.get("folder", "unsorted")),
                        tags=bookmark.get("tags", "")
                    )
                    
                    if result["success"]:
                        results["success"] += 1
                        results["imported"].append(result)
                    else:
                        results["failed"] += 1
                        results["errors"].append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to import JSON bookmarks: {e}")
            return {
                "total": 0,
                "success": 0,
                "failed": 1,
                "errors": [{"error": str(e)}],
                "imported": []
            }
    
    def import_csv_bookmarks(self, file_path: str, dry_run: bool = False) -> Dict[str, Any]:
        """Import bookmarks from CSV file"""
        import csv
        
        results = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "errors": [],
            "imported": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    results["total"] += 1
                    
                    if dry_run:
                        results["imported"].append(row)
                        results["success"] += 1
                    else:
                        result = self.create_bookmark_file(
                            title=row.get("title", row.get("name", "")),
                            uri=row.get("uri", row.get("url", row.get("link", ""))),
                            category=row.get("category", row.get("folder", "unsorted")),
                            tags=row.get("tags", "")
                        )
                        
                        if result["success"]:
                            results["success"] += 1
                            results["imported"].append(result)
                        else:
                            results["failed"] += 1
                            results["errors"].append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to import CSV bookmarks: {e}")
            return {
                "total": 0,
                "success": 0,
                "failed": 1,
                "errors": [{"error": str(e)}],
                "imported": []
            }
    
    def import_pocket_export(self, file_path: str, dry_run: bool = False) -> Dict[str, Any]:
        """Import bookmarks from Pocket export (JSON format)"""
        results = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "errors": [],
            "imported": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Pocket export format
            if "list" in data:
                items = data["list"]
            else:
                items = data
            
            results["total"] = len(items)
            
            for item_id, item in items.items():
                if dry_run:
                    results["imported"].append(item)
                    results["success"] += 1
                else:
                    # Convert Pocket tags to comma-separated string
                    tags = ""
                    if "tags" in item and item["tags"]:
                        tags = ",".join(item["tags"].keys())
                    
                    result = self.create_bookmark_file(
                        title=item.get("resolved_title", item.get("given_title", "")),
                        uri=item.get("resolved_url", item.get("given_url", "")),
                        category="pocket",
                        tags=tags
                    )
                    
                    if result["success"]:
                        results["success"] += 1
                        results["imported"].append(result)
                    else:
                        results["failed"] += 1
                        results["errors"].append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to import Pocket export: {e}")
            return {
                "total": 0,
                "success": 0,
                "failed": 1,
                "errors": [{"error": str(e)}],
                "imported": []
            }
    
    def detect_file_format(self, file_path: str) -> str:
        """Detect the format of the import file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(1024)  # Read first 1KB
            
            # Check for HTML bookmarks format
            if re.search(r'<dt><h3', content, re.IGNORECASE) or re.search(r'<dt><a.*href=', content, re.IGNORECASE):
                return "html"
            
            # Check for JSON format
            if content.strip().startswith('{') or content.strip().startswith('['):
                try:
                    json.loads(content)
                    # Check if it's Pocket format
                    if '"list"' in content or '"given_url"' in content:
                        return "pocket"
                    return "json"
                except json.JSONDecodeError:
                    pass
            
            # Check for CSV format
            if ',' in content and '\n' in content:
                lines = content.split('\n')
                if len(lines) > 1 and ',' in lines[0]:
                    return "csv"
            
            return "unknown"
            
        except Exception as e:
            self.logger.error(f"Failed to detect file format: {e}")
            return "unknown"
    
    def import_file(self, file_path: str, format: str = None, dry_run: bool = False) -> Dict[str, Any]:
        """Import bookmarks from a file, auto-detecting format if not specified"""
        if not os.path.exists(file_path):
            return {
                "total": 0,
                "success": 0,
                "failed": 1,
                "errors": [{"error": f"File not found: {file_path}"}],
                "imported": []
            }
        
        if not format:
            format = self.detect_file_format(file_path)
        
        self.logger.info(f"Importing {format} file: {file_path}")
        
        if format == "html":
            return self.import_html_bookmarks(file_path, dry_run)
        elif format == "json":
            return self.import_json_bookmarks(file_path, dry_run)
        elif format == "csv":
            return self.import_csv_bookmarks(file_path, dry_run)
        elif format == "pocket":
            return self.import_pocket_export(file_path, dry_run)
        else:
            return {
                "total": 0,
                "success": 0,
                "failed": 1,
                "errors": [{"error": f"Unsupported format: {format}"}],
                "imported": []
            } 