#!/usr/bin/env python3
"""Check URLs in a CSV using Python 3.10+ (no extra packages)."""
import argparse
import csv
import socket
import ssl
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from http import HTTPStatus
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler

REPORT_FIELDS = ['URL', 'Detailed response', 'Short result']

FIELDS = ['input', 'checked_url', 'final_url', 'status_code', 'result',
          'redirects', 'response_ms', 'error', 'checked_at_utc']

class Redirects(HTTPRedirectHandler):
    def __init__(self):
        self.history = []
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.history.append(f'{code} {req.full_url} -> {newurl}')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def normalize(value):
    value = value.strip()
    if not value:
        raise ValueError('Empty URL')
    if '://' not in value:
        value = 'https://' + value
    parts = urlsplit(value)
    if parts.scheme.lower() not in ('http', 'https') or not parts.hostname:
        raise ValueError('Expected an HTTP or HTTPS URL')
    if parts.username is not None or parts.password is not None:
        raise ValueError('URLs containing credentials are not supported')
    host = parts.hostname.encode('idna').decode('ascii')
    if any(c.isspace() for c in host):
        raise ValueError('Whitespace in hostname')
    if ':' in host:
        host = '[' + host + ']'
    port = parts.port
    netloc = host + (f':{port}' if port is not None else '')
    return urlunsplit((parts.scheme.lower(), netloc,
                      quote(parts.path or '/', safe="/%:@!$&'()*+,;=-._~"),
                      quote(parts.query, safe="%=&?/:@!$'()*+,;-._~"), ''))

def classify(code):
    if 200 <= code < 300: return 'OK'
    if 300 <= code < 400: return 'REDIRECT'
    if code == 404: return 'NOT_FOUND'
    if code == 503: return 'SERVICE_UNAVAILABLE'
    if code in (401, 403): return 'ACCESS_RESTRICTED'
    if code == 429: return 'RATE_LIMITED'
    if 400 <= code < 500: return 'CLIENT_ERROR'
    if 500 <= code < 600: return 'SERVER_ERROR'
    return 'HTTP_RESPONSE'

def check(value, timeout=15):
    start = time.monotonic()
    row = dict.fromkeys(FIELDS, '')
    row.update(input=value, checked_at_utc=datetime.now(timezone.utc).isoformat())
    redirects = Redirects()
    try:
        url = normalize(value)
        row['checked_url'] = url
        opener = build_opener(redirects)
        req = Request(url, headers={'User-Agent': 'CSVSiteChecker/1.0', 'Accept': '*/*'})
        # GET matches ordinary page requests; only headers are inspected.
        try:
            response = opener.open(req, timeout=timeout)
        except HTTPError as exc:
            response = exc
        with response:
            row.update(final_url=response.geturl(), status_code=response.code,
                       result=classify(response.code))
            if isinstance(response, HTTPError):
                row['error'] = str(response.reason)
    except (ValueError, UnicodeError) as exc:
        row.update(result='INVALID_URL', error=str(exc))
    except Exception as exc:
        reason = exc.reason if isinstance(exc, URLError) else exc
        if isinstance(reason, ssl.SSLError): category = 'TLS_ERROR'
        elif isinstance(reason, socket.gaierror): category = 'DNS_ERROR'
        elif isinstance(reason, (TimeoutError, socket.timeout)): category = 'TIMEOUT'
        else: category = 'CONNECTION_ERROR'
        row.update(result=category, error=str(reason))
    row['redirects'] = ' | '.join(redirects.history)
    row['response_ms'] = round((time.monotonic() - start) * 1000)
    return row

def excel_cell(value):
    """Keep untrusted CSV text from being interpreted as an Excel formula."""
    text = str(value)
    if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')):
        return "'" + text
    return text

def report_row(row):
    code = row['status_code']
    if code:
        try:
            status = HTTPStatus(int(code))
            explanation = f'{code} {status.phrase}: {status.description}'
        except ValueError:
            explanation = f'HTTP {code}'
        short = str(code)
    else:
        explanation = f"{row['result']}: {row['error']}"
        short = 'invalid URL' if row['result'] == 'INVALID_URL' else 'no response'
    details = [explanation, f"Requested: {row['checked_url'] or row['input']}"]
    if row['final_url']:
        details.append(f"Final URL: {row['final_url']}")
    if row['redirects']:
        details.append(f"Redirects: {row['redirects']}")
        destination = row['final_url'] or row['redirects'].rsplit(' -> ', 1)[-1]
        short = f'transfer to {destination} ({short})'
    if code and row['error']:
        details.append(f"Server message: {row['error']}")
    details.extend([f"Elapsed: {row['response_ms']} ms", f"Checked UTC: {row['checked_at_utc']}"])
    return dict(zip(REPORT_FIELDS, map(excel_cell, (row['input'], ' | '.join(details), short))))


def read_urls(path, column=None):
    with open(path, encoding='utf-8-sig', newline='') as handle:
        # Excel's separator hint is metadata, not a URL row.
        start = handle.tell()
        first_line = handle.readline()
        if not (first_line.strip().lower() in ('sep=,', 'sep=;', 'sep=\t')):
            handle.seek(start)
        start = handle.tell()
        sample = handle.read(8192)
        handle.seek(start)
        try: dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
        except csv.Error: dialect = csv.excel
        rows = csv.reader(handle, dialect)
        first = next(rows, None)
        if first is None: return []
        names = [v.strip().lower() for v in first]
        if column is not None:
            if column.lower() not in names:
                raise ValueError(f'Column {column!r} not found in CSV header')
            index = names.index(column.lower())
            data = rows
        else:
            candidates = [i for i, name in enumerate(names)
                          if name in ('url', 'urls', 'website', 'site', 'domain')]
            index = candidates[0] if candidates else 0
            from itertools import chain
            data = rows if candidates else chain([first], rows)
        return [row[index].strip() for row in data
                if len(row) > index and row[index].strip()]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_file', nargs='?', help='Input CSV; opens a file picker if omitted')
    parser.add_argument('-o', '--output', help='Output CSV (default: INPUT_checked.csv)')
    parser.add_argument('--column', help='Name of URL column; otherwise auto-detect or use first column')
    parser.add_argument('--workers', type=int, default=10, help='Parallel checks (default: 10)')
    parser.add_argument('--timeout', type=float, default=15, help='Socket timeout in seconds (default: 15)')
    parser.add_argument('--delimiter', choices=['comma', 'semicolon'], default='comma',
                        help='CSV separator (default: comma); Excel detects it using a sep= line')
    args = parser.parse_args()
    if not 1 <= args.workers <= 100 or not 0 < args.timeout <= 300:
        parser.error('workers must be 1–100; timeout must be greater than 0 and at most 300')
    if not args.csv_file:
        try:
            from tkinter import Tk, filedialog
            root = Tk(); root.withdraw()
            args.csv_file = filedialog.askopenfilename(title='Choose URLs CSV', filetypes=[('CSV files', '*.csv'), ('All files', '*')])
            root.destroy()
        except Exception:
            parser.error('File picker unavailable. Pass a CSV filename on the command line.')
        if not args.csv_file: return
    source = Path(args.csv_file)
    target = Path(args.output) if args.output else source.with_name(source.stem + '_checked.csv')
    if source.resolve() == target.resolve():
        parser.error('Output must differ from the input file')
    try:
        urls = read_urls(source, args.column)
        if not urls: raise ValueError('No URLs found in CSV')
        counts = Counter()
        print(f'Checking {len(urls)} URLs...', flush=True)
        with target.open('w', encoding='utf-8-sig', newline='') as handle:
            delimiter = ',' if args.delimiter == 'comma' else ';'
            handle.write(f'sep={delimiter}\r\n')
            writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS, delimiter=delimiter)
            writer.writeheader()
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                for i, row in enumerate(pool.map(lambda u: check(u, args.timeout), urls), 1):
                    writer.writerow(report_row(row))
                    handle.flush()
                    counts[row['result']] += 1
                    print(f"[{i}/{len(urls)}] {row['input']}: {row['status_code'] or row['result']}", flush=True)
        print(f'\nSaved: {target.resolve()}')
        print(', '.join(f'{key}: {value}' for key, value in sorted(counts.items())))
    except (OSError, ValueError, csv.Error) as exc:
        parser.exit(1, f'Error: {exc}\n')

if __name__ == '__main__':
    main()
