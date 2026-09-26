#!/usr/bin/env python3
"""
Tests for the bookmarks HTTP server: python3 -m unittest test_server (from docker/)
"""

import os
import json
import shutil
import tempfile
import threading
import unittest
import importlib.util
import urllib.error
import urllib.parse
import urllib.request

TEST_DIR = tempfile.mkdtemp()
os.environ['BOOKMARKS_DIR'] = TEST_DIR
os.environ['LOG_FILE'] = ''

HERE = os.path.dirname(os.path.realpath(__file__))
spec = importlib.util.spec_from_file_location('bookmarks_server', os.path.join(HERE, 'bookmarks-server.py'))
bookmarks_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bookmarks_server)

from bookmarks_manager import BookmarksManager

# No network access in tests: every URL is reachable and does not redirect
BookmarksManager.is_uri_accessible = lambda self, uri: True
BookmarksManager.get_final_uri = lambda self, url: url


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = bookmarks_server.ThreadingHTTPServer(('127.0.0.1', 0), bookmarks_server.ServerHandler)
        cls.base = 'http://127.0.0.1:{}'.format(cls.httpd.server_address[1])
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        shutil.rmtree(TEST_DIR, ignore_errors=True)

    def request(self, method, path, body=None, content_type=None):
        request = urllib.request.Request(self.base + path, data=body, method=method)
        if content_type:
            request.add_header('Content-Type', content_type)
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def api_add(self, **fields):
        status, _, body = self.request('POST', '/api/add', json.dumps(fields).encode(), 'application/json')
        return status, json.loads(body)

    def search(self, query, path='/api/search'):
        extra = '&format=json' if path == '/search' else ''
        status, _, body = self.request('GET', '{}?q={}{}'.format(path, urllib.parse.quote(query), extra))
        self.assertEqual(status, 200)
        return json.loads(body)

    def test_api_add_keeps_query_string_intact(self):
        url = 'https://example.com/page?a=1&b=two+words'
        status, result = self.api_add(url=url, title='Query & string', category='tests', tags='one,two')
        self.assertEqual(status, 200, result)
        found = self.search('example.com/page')
        self.assertEqual([b['url'] for b in found], [url])
        self.assertEqual(found[0]['category'], 'tests')

    def test_api_add_requires_url(self):
        status, result = self.api_add(title='No url')
        self.assertEqual(status, 400)
        self.assertIn('error', result)

    def test_legacy_form_add_is_url_decoded(self):
        body = urllib.parse.urlencode({'url': 'https://decoded.example/x?y=1&z=2', 'title': 'Decoded form', 'category': 'tests'})
        status, _, response = self.request('POST', '/add', body.encode(), 'application/x-www-form-urlencoded')
        self.assertEqual(status, 200)
        self.assertNotIn('error', json.loads(response))
        self.assertEqual([b['url'] for b in self.search('decoded.example')], ['https://decoded.example/x?y=1&z=2'])

    def test_multi_word_search(self):
        self.api_add(url='https://multi.example/', title='Glow markdown reader', category='tests')
        self.assertEqual(len(self.search('markdown reader')), 1)
        self.assertEqual(len(self.search('markdown reader', path='/search')), 1)

    def test_api_remove(self):
        self.api_add(url='https://remove.example/', title='Remove me', category='tests')
        bookmark_id = self.search('remove.example')[0]['id']
        status, _, body = self.request('DELETE', '/api/remove', json.dumps({'id': bookmark_id}).encode(), 'application/json')
        self.assertEqual(status, 200, body)
        self.assertEqual(self.search('remove.example'), [])

    def test_web_ui_paths(self):
        for path in ['/', '/share?text=hello', '/manifest.json', '/app.js', '/import', '/export']:
            status, _, _ = self.request('GET', path)
            self.assertEqual(status, 200, path)

    def test_static_files_cannot_escape_static_dir(self):
        for path in ['/../config.py', '/%2e%2e/test_server.py', '/../../etc/passwd']:
            status, _, _ = self.request('GET', path)
            self.assertEqual(status, 404, path)

    def test_import_upload_and_export(self):
        html = b'<DL><DT><A HREF="https://imported.example/">Imported bookmark</A></DL>'
        boundary = 'testboundary'
        body = (
            '--{b}\r\nContent-Disposition: form-data; name="file"; filename="bookmarks.html"\r\n'
            'Content-Type: text/html\r\n\r\n'
        ).format(b=boundary).encode() + html + (
            '\r\n--{b}\r\nContent-Disposition: form-data; name="format"\r\n\r\nhtml\r\n--{b}--\r\n'
        ).format(b=boundary).encode()
        status, _, response = self.request('POST', '/import', body, 'multipart/form-data; boundary=' + boundary)
        self.assertEqual(status, 200)
        self.assertIn(b'Successfully imported 1', response)
        self.assertEqual(len(self.search('imported.example')), 1)

        status, headers, response = self.request('GET', '/export/download?format=json')
        self.assertEqual(status, 200)
        self.assertIn('attachment', headers.get('Content-Disposition'))
        self.assertIn('https://imported.example/', response.decode())


if __name__ == '__main__':
    unittest.main()
