#!/usr/bin/env python3
"""
    Create simple HTTP server to handle requests from client, get the
    search value, use it to fuzzy search the files in the directory and
    send back the results to the client
"""

import os
import json
import logging
import cgi
import tempfile
import shutil
from http.server import BaseHTTPRequestHandler, HTTPServer
from bookmarks_manager import BookmarksManager
from bookmarks_importer import BookmarksImporter
from config import PORT, HOST, BOOKMARKS_DIR, DEBUG, LOG_FILE

# Ensure log directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=DEBUG,
    format='%(asctime)s - %(message)s'
)

PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Bookmarks</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css" />
    <link rel="icon" type="image/png" href="/favicon.png">
  </head>
  <body>
    <main class="container">
    {}
    </main>
  </body>
</html>
""";


class Server:
    def __init__(self, port=None, host=None):
        self.port = port or PORT
        self.host = host or HOST

    def run(self):
        """
            Run the server
        """
        logging.info('Server running on {}:{}'.format(self.host, self.port))
        server_address = (self.host, self.port)
        httpd = HTTPServer(server_address, ServerHandler)
        httpd.serve_forever()

class ServerHandler(BaseHTTPRequestHandler):
    _bookmarks_manager = None
    
    @classmethod
    def get_bookmarks_manager(cls):
        if cls._bookmarks_manager is None:
            cls._bookmarks_manager = BookmarksManager()
        return cls._bookmarks_manager
    
    @property
    def bookmarks_manager(self):
        return self.get_bookmarks_manager()
    
    def do_GET(self):
        """
            Handle GET request from client
        """
        static_dir = os.path.dirname(os.path.realpath(__file__)) + '/static'
        if self.path.startswith('/search'):
            self.handle_search()
            return

        elif self.path.startswith('/form'):
            self.handle_form()
            return
        elif self.path.startswith('/import'):
            self.handle_import()
            return

        elif os.path.exists(static_dir + self.path) and os.path.isfile(static_dir + self.path):
            extension = os.path.splitext(self.path)[1]
            extension_to_content_type = {
                '.js': 'application/javascript',
                '.json': 'application/json',
                '.html': 'text/html',
                '.svg': 'image/svg+xml',
                '.css': 'text/css',
                '.png': 'image/png',
            }
            if extension not in extension_to_content_type:
                self.handle_error(404, 'Invalid extension ' + extension)
                return

            self.send_response(200)
            self.send_header('Content-type', extension_to_content_type[extension])
            self.end_headers()

            binary_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.woff', '.woff2', '.ttf', '.eot', '.otf']
            if extension in binary_extensions:
                with open(static_dir + self.path, 'rb') as f:
                    self.wfile.write(f.read())
                return
            else:
                with open(static_dir + self.path, 'r') as f:
                    self.wfile.write(bytes(f.read(), 'utf-8'))
            return

        elif self.path == '/' or self.path == '':
            main_content = '''
            <div class="container">
                <h1>Bookmarks Server</h1>
                <p>Welcome to the bookmarks management server.</p>
                
                <div class="grid">
                    <div>
                        <h3>Search Bookmarks</h3>
                        <p>Search through your bookmarks by title, tags, or content.</p>
                        <a href="/search?q=" role="button">Search</a>
                    </div>
                    <div>
                        <h3>Add Bookmark</h3>
                        <p>Add a new bookmark to your collection.</p>
                        <a href="/form" role="button">Add Bookmark</a>
                    </div>
                    <div>
                        <h3>Import Bookmarks</h3>
                        <p>Import bookmarks from HTML, JSON, CSV, or Pocket export files.</p>
                        <a href="/import" role="button">Import</a>
                    </div>
                </div>
                
                <hr>
                <p><small>Go to <a href="https://github.com/ArtBIT/bash-bookmarks">Bash bookmarks</a> for more info.</small></p>
            </div>
            '''
            result = PAGE_TEMPLATE.format(main_content)
            # Send the result back to the client
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes(result, 'utf-8'))
            return

        logging.info('Invalid path ' + self.path)
        return

    def do_POST(self):
        """
            Handle POST request from client
        """
        logging.info('POST request')
        if self.path.startswith('/add'):
            self.handle_add()
            return

        return

    def do_OPTIONS(self):
        """
            Handle OPTION request from client
        """
        logging.info('OPTION request')
        if self.path.startswith('/add'):
            self.send_response(200)
            self.send_cors_headers()
            self.end_headers()
            return

        return

    def handle_form(self):
        
        form = """
        <form action="/add" method="post">
            <label for="url">Url</label>
            <input type="text" id="url" name="url" required>
            <label for="title">Title</label>
            <input type="text" id="title" name="title" required>
            <label for="category">Category</label>
            <input type="text" id="category" name="category" required>
            <input type="submit" value="Add">
        </form>

        """
        result = PAGE_TEMPLATE.format(form)
        # Send the result back to the client
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes(result, 'utf-8'))


    def handle_error(self, code, message):
        """
            Handle error response
        """
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(bytes(json.dumps({'error': message}), 'utf-8'))

    def handle_search(self):
        """
            Handle search request from client
        """
        self.parse_params()
        search_value = self.get_params.get('q', '')
        format = self.get_params.get('format', 'html')
        logging.info('Searching for {}'.format(search_value))

        # Use the Python bookmarks manager instead of subprocess
        try:
            logging.info('Starting search for: {} with format: {}'.format(search_value, format))
            
            if format == 'json':
                # For JSON format, get the raw JSON string
                logging.info('Getting JSON result...')
                result = self.bookmarks_manager.suggest_bookmarks(search_value)
                logging.info('Got result, length: {}'.format(len(result)))
                # Send the JSON string directly
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(bytes(result, 'utf-8'))
                logging.info('JSON response sent successfully')
            else:
                # For other formats, parse and format the result
                result = self.bookmarks_manager.suggest_bookmarks(search_value)
                logging.debug('Result: {}'.format(result))
                result_data = json.loads(result)
                self.output_result(result_data, format)
        except Exception as e:
            logging.error('Error searching for {}: {}'.format(search_value, e))
            import traceback
            logging.error('Traceback: {}'.format(traceback.format_exc()))
            # Send error response directly for JSON format
            error_response = json.dumps({'error': 'Error searching for {}'.format(search_value), 'details': str(e)})
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(bytes(error_response, 'utf-8'))
            return

    def handle_import(self):
        """
            Handle import request from client
        """
        if self.command == 'GET':
            self.handle_import_form()
        elif self.command == 'POST':
            self.handle_import_upload()
        else:
            self.send_error(405, "Method not allowed")

    def handle_import_form(self):
        """
            Show import form
        """
        form = """
        <div class="container">
            <h2>Import Bookmarks</h2>
            <p>Upload a bookmarks file to import. Supported formats:</p>
            <ul>
                <li><strong>HTML Bookmarks</strong> - Netscape/Firefox/Chrome bookmarks.html</li>
                <li><strong>JSON</strong> - JSON bookmark files</li>
                <li><strong>CSV</strong> - Comma-separated values</li>
                <li><strong>Pocket Export</strong> - Pocket JSON export</li>
            </ul>
            
            <form action="/import" method="post" enctype="multipart/form-data">
                <label for="file">Select file:</label>
                <input type="file" id="file" name="file" accept=".html,.json,.csv,.txt" required>
                <br><br>
                <label for="format">Format (auto-detected if not specified):</label>
                <select id="format" name="format">
                    <option value="">Auto-detect</option>
                    <option value="html">HTML Bookmarks</option>
                    <option value="json">JSON</option>
                    <option value="csv">CSV</option>
                    <option value="pocket">Pocket Export</option>
                </select>
                <br><br>
                <label for="dry_run">Dry run (preview only):</label>
                <input type="checkbox" id="dry_run" name="dry_run" value="1">
                <br><br>
                <input type="submit" value="Import Bookmarks">
            </form>
            
            <br>
            <p><a href="/">← Back to main page</a></p>
        </div>
        """
        result = PAGE_TEMPLATE.format(form)
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes(result, 'utf-8'))

    def handle_import_upload(self):
        """
            Handle file upload and import
        """
        try:
            # Parse multipart form data
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_error(400, "Invalid content type")
                return
            
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "No file uploaded")
                return
            
            # Read the request body
            body = self.rfile.read(content_length)
            
            # Parse multipart data
            boundary = content_type.split('boundary=')[1]
            parts = self._parse_multipart(body, boundary)
            
            if 'file' not in parts:
                self.send_error(400, "No file uploaded")
                return
            
            file_data = parts['file']
            format_override = parts.get('format', [''])[0]
            dry_run = parts.get('dry_run', [''])[0] == '1'
            
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_file:
                temp_file.write(file_data['data'])
                temp_path = temp_file.name
            
            try:
                # Import the file
                importer = BookmarksImporter()
                result = importer.import_file(temp_path, format_override, dry_run)
                
                # Format result for display
                if result['success'] > 0:
                    status = "success"
                    message = f"Successfully imported {result['success']} bookmarks"
                    if result['failed'] > 0:
                        message += f" ({result['failed']} failed)"
                else:
                    status = "error"
                    message = f"Import failed: {result['errors'][0]['error'] if result['errors'] else 'Unknown error'}"
                
                # Create result HTML
                result_html = f"""
                <div class="container">
                    <h2>Import Result</h2>
                    <div class="alert alert-{status}">
                        <strong>{message}</strong>
                    </div>
                    
                    <h3>Summary</h3>
                    <ul>
                        <li>Total items: {result['total']}</li>
                        <li>Successfully imported: {result['success']}</li>
                        <li>Failed: {result['failed']}</li>
                    </ul>
                """
                
                if result['errors']:
                    result_html += "<h3>Errors</h3><ul>"
                    for error in result['errors']:
                        result_html += f"<li>{error.get('error', 'Unknown error')}</li>"
                    result_html += "</ul>"
                
                if result['imported'] and len(result['imported']) <= 10:
                    result_html += "<h3>Imported Items</h3><ul>"
                    for item in result['imported'][:10]:
                        title = item.get('title', 'Untitled')
                        uri = item.get('uri', '')
                        result_html += f"<li><strong>{title}</strong> - {uri}</li>"
                    result_html += "</ul>"
                    
                    if len(result['imported']) > 10:
                        result_html += f"<p>... and {len(result['imported']) - 10} more items</p>"
                
                result_html += '<br><p><a href="/import">← Import another file</a> | <a href="/">← Back to main page</a></p></div>'
                
                # Send response
                result_page = PAGE_TEMPLATE.format(result_html)
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(bytes(result_page, 'utf-8'))
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            logging.error(f"Import error: {e}")
            error_html = f"""
            <div class="container">
                <h2>Import Error</h2>
                <div class="alert alert-error">
                    <strong>Error during import:</strong> {str(e)}
                </div>
                <p><a href="/import">← Try again</a> | <a href="/">← Back to main page</a></p>
            </div>
            """
            result_page = PAGE_TEMPLATE.format(error_html)
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes(result_page, 'utf-8'))

    def _parse_multipart(self, body, boundary):
        """
            Parse multipart form data
        """
        parts = {}
        boundary = boundary.encode('utf-8')
        
        # Split by boundary
        sections = body.split(b'--' + boundary)
        
        for section in sections:
            if not section.strip() or section.strip() == b'--':
                continue
            
            # Split section into headers and data
            if b'\r\n\r\n' in section:
                headers_part, data = section.split(b'\r\n\r\n', 1)
            else:
                continue
            
            # Parse headers
            headers = {}
            for line in headers_part.decode('utf-8').split('\r\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()
            
            # Get field name from Content-Disposition
            content_disposition = headers.get('Content-Disposition', '')
            name_match = re.search(r'name="([^"]*)"', content_disposition)
            if name_match:
                field_name = name_match.group(1)
                
                # Check if it's a file
                filename_match = re.search(r'filename="([^"]*)"', content_disposition)
                if filename_match:
                    # It's a file
                    parts[field_name] = {
                        'filename': filename_match.group(1),
                        'data': data
                    }
                else:
                    # It's a regular field
                    if field_name not in parts:
                        parts[field_name] = []
                    parts[field_name].append(data.decode('utf-8'))
        
        return parts

    def handle_add(self):
        """
            Handle add request from client
        """
        self.parse_params()
        url = self.post_params.get('url', '')
        title = self.post_params.get('title', '')
        category = self.post_params.get('category', '')
        tags = self.post_params.get('tags', '')
        logging.info('Adding {} {} {} {}'.format(url, title, category, tags))

        # Use the Python bookmarks manager instead of subprocess
        try:
            result = self.bookmarks_manager.add_bookmark(url, title, category, tags)
            
            if 'error' in result:
                logging.error('Error adding bookmark: {}'.format(result['error']))
                # Send error response directly for JSON format
                error_response = json.dumps(result)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(bytes(error_response, 'utf-8'))
                return
            
            logging.info('Bookmark added successfully: {}'.format(result.get('filename', 'unknown')))
            # Send success response directly for JSON format
            success_response = json.dumps(result)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(bytes(success_response, 'utf-8'))
            
        except Exception as e:
            logging.error('Error adding bookmark: {}'.format(e))
            # Send error response directly for JSON format
            error_response = json.dumps({'error': 'Error adding bookmark', 'message': str(e)})
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(bytes(error_response, 'utf-8'))
            return

    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, PUT, DELETE')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Max-Age', '86400')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')

    def output_result(self, result, format):
        """
            Output the result to the client
        """
        logging.info('Output format: {}'.format(format))
        
        if format == 'text':
            # Send the result back to the client
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            # convert json to text
            result = '\n'.join([obj.get('url') for obj in result])
            self.wfile.write(bytes(str(result), 'utf-8'))

            return
        if format == 'html':
            # transform a list of uris to a html list of anchor tags
            result = ['<li><a href="{}">{}</a></li>'.format(o.get('title'), o.get('url')) for o in result]
            result = ''.join(result)
            result = '<ul>' + result + '</ul>'
            result = PAGE_TEMPLATE.format(result)
            # Send the result back to the client
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes(result, 'utf-8'))

    def parse_params(self):
        """
            Parse the GET and POST parameters from the request
        """
        self.parse_get_params()
        self.parse_post_params()

    def parse_get_params(self):
        """
            Parse the GET parameters from the URL
        """
        # Parse the GET parameters
        self.get_params = {}
        if '?' in self.path:
            try:
                query_string = self.path.split('?')[1]
                for param in query_string.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        self.get_params[key] = value
                    else:
                        # Handle parameters without values
                        self.get_params[param] = ''
            except Exception as e:
                logging.error(f"Error parsing GET parameters: {e}")
                self.get_params = {}

        logging.info('GET path: {}'.format(self.path))
        logging.info('GET params: {}'.format(self.get_params))

    def parse_post_params(self):
        """
            Parse the POST parameters from the request body
        """
        # Parse the POST parameters
        self.post_params = {}
        if self.headers.get('Content-Length'):
            content_length = int(self.headers.get('Content-Length'))

            body = self.rfile.read(content_length)
            # parse json body
            if self.headers.get('Content-Type') == 'application/json':
                self.post_params = json.loads(body.decode('utf-8'))
            else:
                # parse url encoded body
                self.post_params = dict([p.split('=') for p in body.decode('utf-8').split('&')])

    def search_files(self, search_value):
        """
            Search all the files in the directory, and their contents for the search value
        """


# Start the server
server = Server()
server.run()

