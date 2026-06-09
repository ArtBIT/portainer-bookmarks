import os
import re
import json
import csv
import io
import html
import logging
from typing import List, Dict, Any


class BookmarksExporter:
    def __init__(self, bookmarks_dir=None):
        self.bookmarks_dir = bookmarks_dir or os.environ.get('BOOKMARKS_DIR', '/data/bookmarks')
        self.logger = logging.getLogger(__name__)

    def _read_all_bookmarks(self) -> List[Dict[str, Any]]:
        if not os.path.isdir(self.bookmarks_dir):
            return []

        bookmarks = []
        for root, dirs, files in os.walk(self.bookmarks_dir):
            if root == self.bookmarks_dir:
                continue
            category = os.path.basename(root)
            for file in files:
                if not file.endswith('.md'):
                    continue
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    title_match = re.search(r'title:\s*(.+)', content)
                    uri_match = re.search(r'uri:\s*(.+)', content)
                    tags_match = re.search(r'tags:\s*\[(.+)\]', content)
                    add_date_match = re.search(r'add_date:\s*(.+)', content)
                    last_modified_match = re.search(r'last_modified:\s*(.+)', content)

                    title = title_match.group(1).strip() if title_match else ''
                    uri = uri_match.group(1).strip() if uri_match else ''
                    tags_str = tags_match.group(1).strip() if tags_match else ''
                    tags = [t.strip() for t in tags_str.split(',') if t.strip()] if tags_str else []
                    add_date = add_date_match.group(1).strip() if add_date_match else ''
                    last_modified = last_modified_match.group(1).strip() if last_modified_match else ''

                    bookmarks.append({
                        'title': title,
                        'uri': uri,
                        'category': category,
                        'tags': tags,
                        'add_date': add_date,
                        'last_modified': last_modified,
                    })
                except Exception as e:
                    self.logger.warning(f'Failed to read bookmark {file_path}: {e}')

        bookmarks.sort(key=lambda b: (b['category'], b['title']))
        return bookmarks

    def export_json(self) -> bytes:
        bookmarks = self._read_all_bookmarks()
        return json.dumps(bookmarks, indent=2, ensure_ascii=False).encode('utf-8')

    def export_html(self) -> bytes:
        bookmarks = self._read_all_bookmarks()

        by_category: Dict[str, list] = {}
        for b in bookmarks:
            by_category.setdefault(b['category'], []).append(b)

        lines = [
            '<!DOCTYPE NETSCAPE-Bookmark-file-1>',
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
            '<TITLE>Bookmarks</TITLE>',
            '<H1>Bookmarks</H1>',
            '<DL><p>',
        ]
        for category in sorted(by_category):
            lines.append(f'    <DT><H3>{html.escape(category)}</H3>')
            lines.append('    <DL><p>')
            for b in by_category[category]:
                add_date_attr = f' ADD_DATE="{html.escape(b["add_date"])}"' if b['add_date'] else ''
                lines.append(f'        <DT><A HREF="{html.escape(b["uri"])}"{add_date_attr}>{html.escape(b["title"])}</A>')
            lines.append('    </DL><p>')
        lines.append('</DL><p>')

        return '\n'.join(lines).encode('utf-8')

    def export_csv(self) -> bytes:
        bookmarks = self._read_all_bookmarks()

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=['title', 'uri', 'category', 'tags'])
        writer.writeheader()
        for b in bookmarks:
            writer.writerow({
                'title': b['title'],
                'uri': b['uri'],
                'category': b['category'],
                'tags': ','.join(b['tags']),
            })
        return buf.getvalue().encode('utf-8')

    def export_file(self, format: str) -> Dict[str, Any]:
        try:
            if format == 'json':
                data = self.export_json()
            elif format == 'html':
                data = self.export_html()
            elif format == 'csv':
                data = self.export_csv()
            else:
                return {'success': False, 'error': f'Unknown format: {format}'}

            bookmarks = self._read_all_bookmarks()
            return {'success': True, 'data': data, 'format': format, 'count': len(bookmarks)}
        except Exception as e:
            self.logger.error(f'Export failed: {e}')
            return {'success': False, 'error': str(e)}
