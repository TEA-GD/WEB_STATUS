# CSV Website Status Checker

Check domains and URLs from a CSV and export HTTP status codes, redirects, and network errors.

## Download and run

Click **Code → Download ZIP**, extract the archive, and open a terminal in the extracted folder. Requires Python 3.10 or newer; no extra packages.

```bash
python site_checker.py your_urls.csv
```

On macOS/Linux, use `python3` if necessary. Run without a filename to open a file picker:

```bash
python site_checker.py
```

CSV SITE CHECKER — Python 3.10 or newer, no extra packages

1. Install Python from https://www.python.org/downloads/
   On Windows, enable "Add Python to PATH" during installation.
2. Open a terminal in the folder containing site_checker.py.
3. Run:
   python site_checker.py your_urls.csv
   (On macOS/Linux, use python3 instead of python if needed.)

Or run without a filename to choose a CSV using a file picker:
   python site_checker.py
The file picker requires Tkinter, included with most desktop Python installations.

Advanced example:
   python site_checker.py urls.csv --column website --workers 5 --timeout 20 -o results.csv

INPUT
UTF-8 CSV, optionally with a header named url, urls, website, site, or domain.
Without a recognized header, the first column is used, including its first row.
Use --column for a different header. Comma, semicolon and tab separators are detected.
Blank URL cells are skipped. Input order and duplicate URLs are preserved.

OUTPUT
By default, a new INPUT_checked.csv appears beside the input.
Includes original input, checked URL, final URL, exact final HTTP status,
category, redirect history, elapsed time, error, and UTC timestamp.
200–299: OK; 404: NOT_FOUND; 503: SERVICE_UNAVAILABLE.
401/403: ACCESS_RESTRICTED; 429: RATE_LIMITED.
Other HTTP codes are reported too. Network failures have a category and no HTTP code.
Redirects are followed; their codes and destinations appear in the redirects column.

INTERPRETATION
404 means that particular page was not found, not that the whole site is offline.
403 may mean bot blocking. A site returning any HTTP status has responded.
Bare domains use HTTPS. To check HTTP explicitly, use http:// in the CSV.
TLS certificates are verified; certificate failures are reported separately.
No automatic fallback to HTTP or retries: failures and transient 503s remain visible.
Checks use GET and close after response headers, without downloading full pages.
Timeout is per socket operation, not a strict total deadline (redirects/DNS can add time).
Results reflect the machine/network running the checker. No browser JavaScript is run,
so soft 404s and error messages embedded in a 200 page cannot be detected.
For rate limits, reduce --workers and run later.
