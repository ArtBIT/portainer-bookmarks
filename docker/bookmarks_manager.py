#!/usr/bin/env python3
"""
Bookmarks Manager - Python implementation of the bash bookmarks functionality
"""

import os
import re
import json
import hashlib
import logging
import urllib.parse
import urllib.request
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import unicodedata


class BookmarksManager:
    """Python implementation of the bash bookmarks functionality"""
    
    def __init__(self, bookmarks_dir: str = None):
        """Initialize the bookmarks manager"""
        self.bookmarks_dir = bookmarks_dir or os.environ.get('BOOKMARKS_DIR', '/data/bookmarks')
        self.curl_options = {
            'timeout': 30,
            'user_agent': 'Bash-Bookmarks/1.0 (X11; Linux x86_64; rv:10.0)'
        }
        
        # Ensure bookmarks directory exists
        os.makedirs(self.bookmarks_dir, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def slugify(self, text: str) -> str:
        """Convert text to a URL-friendly slug"""
        if not text:
            return ""
        
        # Remove accents
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
        
        # Convert to lowercase and replace non-alphanumeric with hyphens
        text = re.sub(r'[^a-zA-Z0-9]', '-', text.lower())
        
        # Remove multiple hyphens and trim
        text = re.sub(r'-+', '-', text)
        text = text.strip('-')
        
        return text
    
    def is_url(self, uri: str) -> bool:
        """Check if URI is a URL"""
        return bool(re.match(r'^https?://', uri))
    
    def is_local_file(self, uri: str) -> bool:
        """Check if URI is a local file path"""
        return (uri.startswith('/') or 
                uri.startswith('~') or 
                uri.startswith('.') or 
                uri.startswith('..'))
    
    def is_file_uri(self, uri: str) -> bool:
        """Check if URI is a file:// URI"""
        return uri.startswith('file://')
    
    def is_file(self, uri: str) -> bool:
        """Check if URI is a file (local or file://)"""
        return self.is_local_file(uri) or self.is_file_uri(uri)
    
    def expand_path(self, uri: str) -> str:
        """Expand relative paths and special characters"""
        if uri == '.':
            return os.getcwd()
        elif uri == '..':
            return os.path.join(os.getcwd(), '..')
        elif uri.startswith('~'):
            return os.path.expanduser(uri)
        elif uri.startswith('./'):
            return os.path.join(os.getcwd(), uri[2:])
        elif uri.startswith('../'):
            return os.path.join(os.getcwd(), '..', uri[3:])
        elif self.is_file_uri(uri):
            return uri[7:]  # Remove file:// prefix
        
        return uri
    
    def is_uri_accessible(self, uri: str) -> bool:
        """Check if URI is accessible"""
        try:
            if self.is_url(uri):
                # Check HTTP status
                req = urllib.request.Request(uri, headers={'User-Agent': self.curl_options['user_agent']})
                with urllib.request.urlopen(req, timeout=self.curl_options['timeout']) as response:
                    return 200 <= response.status < 400
            elif self.is_file(uri):
                # Check if file is readable
                expanded_path = self.expand_path(uri)
                return os.access(expanded_path, os.R_OK)
            else:
                return False
        except Exception as e:
            self.logger.debug(f"URI accessibility check failed for {uri}: {e}")
            return False
    
    def get_title_from_uri(self, uri: str) -> str:
        """Extract title from URI"""
        try:
            if self.is_url(uri):
                # Fetch HTML and extract title
                req = urllib.request.Request(uri, headers={'User-Agent': self.curl_options['user_agent']})
                with urllib.request.urlopen(req, timeout=self.curl_options['timeout']) as response:
                    html = response.read().decode('utf-8', errors='ignore')
                    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                    if title_match:
                        return title_match.group(1).strip()
            elif self.is_file(uri):
                # For files, use basename
                expanded_path = self.expand_path(uri)
                return os.path.basename(expanded_path)
        except Exception as e:
            self.logger.debug(f"Failed to get title from URI {uri}: {e}")
        
        return ""
    
    def get_final_uri(self, url: str) -> str:
        """Get final URL after following redirects"""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': self.curl_options['user_agent']})
            with urllib.request.urlopen(req, timeout=self.curl_options['timeout']) as response:
                return response.url
        except Exception as e:
            self.logger.debug(f"Failed to get final URI for {url}: {e}")
            return url
    
    def create_bookmark(self, title: str = "", uri: str = "", category: str = "", 
                       tags: str = "", name: str = "", force: bool = False) -> Dict[str, str]:
        """Create a new bookmark"""
        try:
            # Validate inputs
            if not uri:
                return {"error": "URI cannot be empty"}
            
            # Expand and normalize URI
            if self.is_file(uri):
                uri = self.expand_path(uri)
                uri = os.path.realpath(uri)
            
            if self.is_url(uri):
                uri = self.get_final_uri(uri)
            
            # Check if URI is accessible
            if not self.is_uri_accessible(uri):
                return {"error": f"URI is not accessible: {uri}"}
            
            # Set default category
            if not category:
                if self.is_local_file(uri):
                    category = "files"
                else:
                    category = "unsorted"
            
            # Get title if not provided
            if not title:
                title = self.get_title_from_uri(uri)
            
            # If title is still empty, infer from URI
            if not title:
                title = os.path.basename(uri.rstrip('/'))
            
            # Set name if not provided
            if not name:
                name = title
            
            # Validate required fields
            if not title:
                return {"error": f"Title cannot be empty for {uri}"}
            if not category:
                return {"error": f"Category cannot be empty for {title}"}
            
            # Slugify category and name
            category = self.slugify(category)
            name = self.slugify(name)
            
            # Create category directory
            category_dir = os.path.join(self.bookmarks_dir, category)
            os.makedirs(category_dir, exist_ok=True)
            
            # Create filename
            filename = os.path.join(category_dir, f"{name}.md")
            
            # Check if file exists
            if os.path.exists(filename) and not force:
                return {"error": f"File already exists: {filename}"}
            
            # Prepare tags
            if tags:
                all_tags = f"{category},{tags}"
            else:
                all_tags = category
            
            # Create markdown content
            content = f"""---
title: {title}
uri: {uri}
tags: [{all_tags}]
---
[{title}]({uri})
"""
            
            # Write file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"Created bookmark: {filename}")
            return {
                "success": "Bookmark created successfully",
                "filename": filename,
                "title": title,
                "uri": uri,
                "category": category,
                "tags": all_tags
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create bookmark: {e}")
            return {"error": f"Failed to create bookmark: {str(e)}"}
    
    def search_bookmarks(self, query: str, limit: int = 20) -> List[Dict[str, str]]:
        """Search bookmarks by content"""
        if len(query) < 3:
            return []
        
        try:
            results = []
            query_lower = query.lower()
            
            # Walk through all markdown files
            for root, dirs, files in os.walk(self.bookmarks_dir):
                for file in files:
                    if file.endswith('.md'):
                        file_path = os.path.join(root, file)
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                                # Check if query matches content
                                if query_lower in content.lower():
                                    # Extract metadata
                                    title_match = re.search(r'title:\s*(.+)', content)
                                    uri_match = re.search(r'uri:\s*(.+)', content)
                                    tags_match = re.search(r'tags:\s*\[(.+)\]', content)
                                    
                                    title = title_match.group(1).strip() if title_match else ""
                                    uri = uri_match.group(1).strip() if uri_match else ""
                                    tags_str = tags_match.group(1).strip() if tags_match else ""
                                    
                                    # Parse tags
                                    tags = []
                                    if tags_str:
                                        tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                                    
                                    # Get category from path
                                    category = os.path.basename(root)
                                    
                                    # Generate unique ID
                                    file_id = hashlib.md5(file_path.encode()).hexdigest()
                                    
                                    results.append({
                                        "id": file_id,
                                        "url": uri,
                                        "title": title,
                                        "tags": tags,
                                        "category": category
                                    })
                                    
                                    # Limit results
                                    if len(results) >= limit:
                                        break
                        except Exception as e:
                            self.logger.debug(f"Failed to read file {file_path}: {e}")
                            continue
                
                if len(results) >= limit:
                    break
            
            return results
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []
    
    def suggest_bookmarks(self, query: str) -> str:
        """Suggest bookmarks (returns JSON string like the bash script)"""
        results = self.search_bookmarks(query)
        return json.dumps(results)
    
    def add_bookmark(self, url: str, title: str, category: str, tags: str = "") -> Dict[str, str]:
        """Add a bookmark (API-friendly wrapper)"""
        return self.create_bookmark(
            title=title,
            uri=url,
            category=category,
            tags=tags
        ) 