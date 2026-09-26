#!/usr/bin/env python3
"""
    Bookmarks server: stores bookmarks as markdown files, serves the web UI
    (installable as a PWA) and the HTTP API used by the CLI, the Firefox
    add-on and the web UI.
"""

import os
import re
import ssl
import html
import json
import logging
import tempfile
import datetime
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from bookmarks_manager import BookmarksManager
from bookmarks_importer import BookmarksImporter
from bookmarks_exporter import BookmarksExporter
from config import PORT, HOST, BOOKMARKS_DIR, DEBUG, LOG_FILE, TLS_CERT, TLS_KEY

# Configure logging, to a file when LOG_FILE is set, otherwise to stderr
if LOG_FILE:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE or None,
    level=DEBUG,
    format='%(asctime)s - %(message)s'
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static')

# Paths that serve the web UI (/share is the PWA share target)
APP_PATHS = ['/', '/share', '/index.html']

CONTENT_TYPES = {
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.webmanifest': 'application/manifest+json',
    '.html': 'text/html; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.css': 'text/css',
    '.png': 'image/png',
}

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <meta name="theme-color" content="#1e1549" />
    <title>Bookmarks</title>
    <link rel="icon" type="image/png" href="/favicon.png" />
    <link rel="stylesheet" href="/app.css" />
  </head>
  <body>
    <header class="bar">
      <a href="/" class="home"><img src="/icon.svg" alt="" class="logo" /><h1>Bookmarks</h1></a>
    </header>
    <main class="page">
    {}
    </main>
  </body>
</html>
"""


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
        httpd = ThreadingHTTPServer(server_address, ServerHandler)
        if TLS_CERT and TLS_KEY:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(TLS_CERT, TLS_KEY)
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
            logging.info('TLS enabled')
        httpd.serve_forever()


class ServerHandler(BaseHTTPRequestHandler):
    _bookmarks_manager = None

    @classmethod
    def get_bookmarks_manager(cls):
        if cls._bookmarks_manager is None:
            cls._bookmarks_manager = BookmarksManager(BOOKMARKS_DIR)
        return cls._bookmarks_manager

    @property
    def bookmarks_manager(self):
        return self.get_bookmarks_manager()

    @property
    def route(self):
        return urllib.parse.urlsplit(self.path).path

    def do_GET(self):
        """
            Handle GET request from client
        """
        path = self.route
        if path == '/api/search':
            self.handle_api_search()

        elif path.startswith('/search'):
            self.handle_search()

        elif path.startswith('/form'):
            self.handle_form()

        elif path.startswith('/import'):
            self.handle_import_form()

        elif path.startswith('/export/download'):
            self.handle_export_download()

        elif path.startswith('/export'):
            self.handle_export()

        elif path in APP_PATHS:
            self.serve_static('/index.html')

        elif not self.serve_static(path):
            logging.info('Invalid path ' + self.path)
            self.handle_error(404, 'Not found')

    def do_POST(self):
        """
            Handle POST request from client
        """
        path = self.route
        if path == '/api/add':
            self.handle_api_add()

        elif path.startswith('/add'):
            self.handle_add()

        elif path.startswith('/import'):
            self.handle_import_upload()

        else:
            self.handle_error(404, 'Not found')

    def do_DELETE(self):
        """
            Handle DELETE request from client
        """
        path = self.route
        if path == '/api/remove':
            self.handle_api_remove()

        elif path.startswith('/remove'):
            self.handle_remove()

        else:
            self.handle_error(404, 'Not found')

    def do_OPTIONS(self):
        """
            Handle OPTION request from client
        """
        if self.route.startswith(('/add', '/remove', '/api/')):
            self.send_response(200)
            self.send_cors_headers()
            self.end_headers()
            return

        self.handle_error(404, 'Not found')

    def serve_static(self, path):
        """
            Serve a file from the static directory, returns False if not found
        """
        file_path = os.path.realpath(os.path.join(STATIC_DIR, path.lstrip('/')))
        if not file_path.startswith(STATIC_DIR + os.sep) or not os.path.isfile(file_path):
            return False

        extension = os.path.splitext(file_path)[1]
        if extension not in CONTENT_TYPES:
            return False

        with open(file_path, 'rb') as f:
            content = f.read()
        self.send_response(200)
        self.send_header('Content-type', CONTENT_TYPES[extension])
        self.send_header('Cache-Control', 'no-cache')
        if path == '/service-worker.js':
            self.send_header('Service-Worker-Allowed', '/')
        self.end_headers()
        self.wfile.write(content)
        return True

    def send_page(self, content, code=200):
        self.send_response(code)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(bytes(PAGE_TEMPLATE.format(content), 'utf-8'))

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(bytes(json.dumps(data), 'utf-8'))

    def handle_form(self):
        form = """
        <h2>Add bookmark</h2>
        <form action="/add" method="post">
            <label for="url">Url <input type="text" id="url" name="url" required></label>
            <label for="title">Title <input type="text" id="title" name="title" required></label>
            <label for="category">Category <input type="text" id="category" name="category" required></label>
            <div class="actions"><button type="submit" class="primary">Add</button></div>
        </form>
        """
        self.send_page(form)

    def handle_error(self, code, message):
        """
            Handle error response
        """
        self.send_json({'error': message}, code)

    def handle_api_search(self):
        """
            Search for the web UI, always JSON
        """
        self.parse_get_params()
        query = self.get_params.get('q', '').strip()
        try:
            self.send_json(self.bookmarks_manager.search_bookmarks(query))
        except Exception as e:
            logging.error('Error searching for {}: {}'.format(query, e))
            self.handle_error(500, 'Error searching for {}'.format(query))

    def handle_api_add(self):
        """
            Add a bookmark from the web UI (JSON body)
        """
        self.parse_post_params()
        url = str(self.post_params.get('url') or '').strip()
        if not url:
            self.handle_error(400, 'url is required')
            return

        tags = self.post_params.get('tags') or ''
        if isinstance(tags, list):
            tags = ','.join(tags)

        try:
            result = self.bookmarks_manager.add_bookmark(
                url,
                str(self.post_params.get('title') or '').strip(),
                str(self.post_params.get('category') or 'unsorted').strip(),
                str(tags).strip(),
            )
        except Exception as e:
            logging.error('Error adding bookmark: {}'.format(e))
            result = {'error': 'Error adding bookmark', 'message': str(e)}

        self.send_json(result, 400 if 'error' in result else 200)

    def handle_api_remove(self):
        """
            Remove a bookmark from the web UI (JSON body with id)
        """
        self.parse_post_params()
        file_id = str(self.post_params.get('id') or '')
        if not file_id:
            self.handle_error(400, 'id is required')
            return

        result = self.bookmarks_manager.delete_bookmark(file_id)
        self.send_json(result, 404 if 'error' in result else 200)

    def handle_search(self):
        """
            Handle search request from client
        """
        self.parse_params()
        search_value = self.get_params.get('q', '')
        format = self.get_params.get('format', 'html')
        logging.info('Searching for {}'.format(search_value))

        try:
            result = self.bookmarks_manager.suggest_bookmarks(search_value)
            if format == 'json':
                # Send the JSON string directly
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(bytes(result, 'utf-8'))
            else:
                self.output_result(json.loads(result), format)
        except Exception as e:
            logging.error('Error searching for {}: {}'.format(search_value, e))
            # Errors are sent with status 200 for compatibility with existing clients
            self.send_json({'error': 'Error searching for {}'.format(search_value), 'details': str(e)})

    def handle_import_form(self):
        """
            Show import form
        """
        form = """
            <h2>Import bookmarks</h2>
            <p>Upload a bookmarks file to import. Supported formats:</p>
            <ul>
                <li><strong>HTML Bookmarks</strong>: Netscape/Firefox/Chrome bookmarks.html</li>
                <li><strong>JSON</strong>: JSON bookmark files</li>
                <li><strong>CSV</strong>: Comma-separated values</li>
                <li><strong>Pocket Export</strong>: Pocket JSON export</li>
            </ul>

            <form action="/import" method="post" enctype="multipart/form-data">
                <label for="file">File <input type="file" id="file" name="file" accept=".html,.json,.csv,.txt" required></label>
                <label for="format">Format
                    <select id="format" name="format">
                        <option value="">Auto-detect</option>
                        <option value="html">HTML Bookmarks</option>
                        <option value="json">JSON</option>
                        <option value="csv">CSV</option>
                        <option value="pocket">Pocket Export</option>
                    </select>
                </label>
                <label class="checkbox"><input type="checkbox" id="dry_run" name="dry_run" value="1"> Dry run (preview only)</label>
                <div class="actions"><button type="submit" class="primary">Import bookmarks</button></div>
            </form>
            <p><a href="/">&larr; Back to bookmarks</a></p>
        """
        self.send_page(form)

    def handle_import_upload(self):
        """
            Handle file upload and import
        """
        try:
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data') or 'boundary=' not in content_type:
                self.handle_error(400, 'Invalid content type')
                return

            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.handle_error(400, 'No file uploaded')
                return

            body = self.rfile.read(content_length)
            boundary = content_type.split('boundary=')[1].strip('"')
            parts = self._parse_multipart(body, boundary)

            if 'file' not in parts:
                self.handle_error(400, 'No file uploaded')
                return

            file_data = parts['file']
            format_override = parts.get('format', [''])[0]
            dry_run = parts.get('dry_run', [''])[0] == '1'

            with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_file:
                temp_file.write(file_data['data'])
                temp_path = temp_file.name

            try:
                importer = BookmarksImporter(BOOKMARKS_DIR)
                result = importer.import_file(temp_path, format_override, dry_run)
            finally:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

            if result['success'] > 0:
                status = 'success'
                message = 'Successfully imported {} bookmarks'.format(result['success'])
                if result['failed'] > 0:
                    message += ' ({} failed)'.format(result['failed'])
            else:
                status = 'error'
                message = 'Import failed: {}'.format(result['errors'][0]['error'] if result['errors'] else 'Unknown error')

            esc = html.escape
            result_html = """
                <h2>Import result</h2>
                <div class="alert alert-{}"><strong>{}</strong></div>
                <h3>Summary</h3>
                <ul>
                    <li>Total items: {}</li>
                    <li>Successfully imported: {}</li>
                    <li>Failed: {}</li>
                </ul>
            """.format(status, esc(message), result['total'], result['success'], result['failed'])

            if result['errors']:
                result_html += '<h3>Errors</h3><ul>'
                for error in result['errors']:
                    result_html += '<li>{}</li>'.format(esc(str(error.get('error', 'Unknown error'))))
                result_html += '</ul>'

            if result['imported']:
                result_html += '<h3>Imported items</h3><ul>'
                for item in result['imported'][:10]:
                    result_html += '<li><strong>{}</strong> {}</li>'.format(esc(str(item.get('title', 'Untitled'))), esc(str(item.get('uri', ''))))
                result_html += '</ul>'
                if len(result['imported']) > 10:
                    result_html += '<p>... and {} more items</p>'.format(len(result['imported']) - 10)

            result_html += '<p><a href="/import">&larr; Import another file</a> &middot; <a href="/">Back to bookmarks</a></p>'
            self.send_page(result_html)

        except Exception as e:
            logging.error('Import error: {}'.format(e))
            error_html = """
                <h2>Import error</h2>
                <div class="alert alert-error"><strong>Error during import:</strong> {}</div>
                <p><a href="/import">&larr; Try again</a> &middot; <a href="/">Back to bookmarks</a></p>
            """.format(html.escape(str(e)))
            self.send_page(error_html, 500)

    def handle_export(self):
        """
            Show export form
        """
        form = """
            <h2>Export bookmarks</h2>
            <p>Download all your bookmarks in a standard format.</p>
            <form action="/export/download" method="get">
                <label for="format">Format
                    <select name="format" id="format">
                        <option value="json">JSON (structured data)</option>
                        <option value="html">HTML (Netscape, browser-compatible)</option>
                        <option value="csv">CSV (spreadsheet-compatible)</option>
                    </select>
                </label>
                <div class="actions"><button type="submit" class="primary">Download</button></div>
            </form>
            <p><a href="/">&larr; Back to bookmarks</a></p>
        """
        self.send_page(form)

    def handle_export_download(self):
        """
            Generate and stream the bookmarks file download
        """
        try:
            self.parse_get_params()
            fmt = self.get_params.get('format', 'json')
            if fmt not in ('json', 'html', 'csv'):
                self.handle_error(400, 'Invalid format: {}'.format(fmt))
                return

            date_str = datetime.date.today().strftime('%Y-%m-%d')
            filename = 'bookmarks_{}.{}'.format(date_str, fmt)

            exporter = BookmarksExporter(BOOKMARKS_DIR)
            result = exporter.export_file(fmt)
            if not result['success']:
                self.handle_error(500, result['error'])
                return

            content_types = {
                'json': 'application/json',
                'html': 'text/html; charset=utf-8',
                'csv': 'text/csv; charset=utf-8',
            }
            self.send_response(200)
            self.send_header('Content-type', content_types[fmt])
            self.send_header('Content-Disposition', 'attachment; filename="{}"'.format(filename))
            self.end_headers()
            self.wfile.write(result['data'])
        except Exception as e:
            self.handle_error(500, str(e))

    def _parse_multipart(self, body, boundary):
        """
            Parse multipart form data
        """
        parts = {}
        boundary = boundary.encode('utf-8')

        for section in body.split(b'--' + boundary):
            if not section.strip() or section.strip() == b'--':
                continue

            if b'\r\n\r\n' not in section:
                continue
            headers_part, data = section.split(b'\r\n\r\n', 1)
            # Drop the line break that precedes the next boundary
            if data.endswith(b'\r\n'):
                data = data[:-2]

            headers = {}
            for line in headers_part.decode('utf-8', errors='replace').split('\r\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()

            content_disposition = headers.get('Content-Disposition', '')
            name_match = re.search(r'name="([^"]*)"', content_disposition)
            if not name_match:
                continue

            field_name = name_match.group(1)
            filename_match = re.search(r'filename="([^"]*)"', content_disposition)
            if filename_match:
                parts[field_name] = {'filename': filename_match.group(1), 'data': data}
            else:
                parts.setdefault(field_name, []).append(data.decode('utf-8', errors='replace'))

        return parts

    def handle_add(self):
        """
            Handle add request from client (CLI, Firefox add-on, /form)
        """
        self.parse_params()
        url = self.post_params.get('url', '')
        title = self.post_params.get('title', '')
        category = self.post_params.get('category', '')
        tags = self.post_params.get('tags', '')
        logging.info('Adding {} {} {} {}'.format(url, title, category, tags))

        try:
            result = self.bookmarks_manager.add_bookmark(url, title, category, tags)
            if 'error' in result:
                logging.error('Error adding bookmark: {}'.format(result['error']))
            else:
                logging.info('Bookmark added successfully: {}'.format(result.get('filename', 'unknown')))
        except Exception as e:
            logging.error('Error adding bookmark: {}'.format(e))
            result = {'error': 'Error adding bookmark', 'message': str(e)}

        # Errors are sent with status 200 for compatibility with existing clients
        self.send_json(result)

    def handle_remove(self):
        """
            Handle remove request from client
        """
        self.parse_params()
        file_id = self.post_params.get('id', '')
        logging.info('Removing {}'.format(file_id))

        try:
            result = self.bookmarks_manager.delete_bookmark(file_id)
        except Exception as e:
            logging.error('Error removing bookmark: {}'.format(e))
            result = {'error': 'Error removing bookmark', 'message': str(e)}

        self.send_json(result)

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
        if format == 'text':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(bytes('\n'.join([obj.get('url') for obj in result]), 'utf-8'))
            return

        # transform a list of uris to a html list of anchor tags
        items = ''.join(
            '<li><a href="{}">{}</a></li>'.format(html.escape(o.get('url', '')), html.escape(o.get('title', '') or o.get('url', '')))
            for o in result
        )
        self.send_page('<h2>Search results</h2><ul>{}</ul><p><a href="/">&larr; Back to bookmarks</a></p>'.format(items))

    def parse_params(self):
        """
            Parse the GET and POST parameters from the request
        """
        self.parse_get_params()
        self.parse_post_params()

    def parse_get_params(self):
        """
            Parse and URL-decode the GET parameters
        """
        query = urllib.parse.urlsplit(self.path).query
        self.get_params = dict(urllib.parse.parse_qsl(query, keep_blank_values=True))
        logging.debug('GET params: {}'.format(self.get_params))

    def parse_post_params(self):
        """
            Parse the POST parameters from a JSON or URL encoded request body
        """
        self.post_params = {}
        content_length = int(self.headers.get('Content-Length') or 0)
        if not content_length:
            return

        body = self.rfile.read(content_length).decode('utf-8', errors='replace')
        content_type = self.headers.get('Content-Type', '')
        if content_type.startswith('application/json'):
            try:
                params = json.loads(body or '{}')
            except ValueError:
                params = {}
            self.post_params = params if isinstance(params, dict) else {}
        else:
            self.post_params = dict(urllib.parse.parse_qsl(body, keep_blank_values=True))


if __name__ == '__main__':
    Server().run()
