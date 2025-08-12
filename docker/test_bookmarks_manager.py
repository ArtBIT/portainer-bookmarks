#!/usr/bin/env python3
"""
Test script for BookmarksManager class
"""

import os
import tempfile
import shutil
from bookmarks_manager import BookmarksManager


def test_bookmarks_manager():
    """Test the BookmarksManager functionality"""
    
    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp()
    print(f"Testing in temporary directory: {test_dir}")
    
    try:
        # Initialize manager with test directory
        manager = BookmarksManager(test_dir)
        
        # Test 1: Create a bookmark
        print("\n=== Test 1: Create Bookmark ===")
        result = manager.create_bookmark(
            title="Test Bookmark",
            uri="https://example.com",
            category="test",
            tags="test,docker"
        )
        print(f"Create result: {result}")
        
        # Test 2: Search bookmarks
        print("\n=== Test 2: Search Bookmarks ===")
        search_results = manager.search_bookmarks("test")
        print(f"Search results: {search_results}")
        
        # Test 3: Suggest bookmarks
        print("\n=== Test 3: Suggest Bookmarks ===")
        suggest_results = manager.suggest_bookmarks("test")
        print(f"Suggest results: {suggest_results}")
        
        # Test 4: Add bookmark via API
        print("\n=== Test 4: Add Bookmark via API ===")
        api_result = manager.add_bookmark(
            url="https://python.org",
            title="Python",
            category="programming",
            tags="python,programming"
        )
        print(f"API result: {api_result}")
        
        # Test 5: Search again
        print("\n=== Test 5: Search After Adding ===")
        final_search = manager.search_bookmarks("python")
        print(f"Final search results: {final_search}")
        
        print("\n=== All Tests Completed ===")
        
    finally:
        # Clean up
        shutil.rmtree(test_dir)
        print(f"Cleaned up temporary directory: {test_dir}")


if __name__ == "__main__":
    test_bookmarks_manager() 