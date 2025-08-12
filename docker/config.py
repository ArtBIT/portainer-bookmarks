"""
Configuration file for the bookmarks server
"""
import os

# Server configuration
DEFAULT_PORT = 9080
DEFAULT_HOST = '0.0.0.0'

# Get configuration from environment variables with defaults
PORT = int(os.environ.get('PORT', DEFAULT_PORT))
HOST = os.environ.get('HOST', DEFAULT_HOST)
BOOKMARKS_DIR = os.environ.get('BOOKMARKS_DIR', '/data/bookmarks')
DEBUG = os.environ.get('DEBUG', 'INFO')
LOG_FILE = os.environ.get('LOG_FILE', '/data/logs/bookmarks-server.log')

# Server URLs
SERVER_URL = f"http://localhost:{PORT}"
HEALTH_CHECK_URL = f"http://localhost:{PORT}/"

# File upload configuration
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.html', '.json', '.csv', '.txt'}

# Import configuration
SUPPORTED_FORMATS = ['html', 'json', 'csv', 'pocket'] 