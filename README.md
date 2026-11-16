# CSV Website Status Checker

Check domains and URLs from a CSV and save an Excel-friendly report. Requires Python 3.10 or newer; no extra packages.

## Download and run

Click **Code → Download ZIP**, extract the archive, and open a terminal in the extracted folder.

```bash
python site_checker.py your_urls.csv
```

On macOS/Linux use `python3` if necessary. Run without a filename to choose a CSV with a file picker (requires Tkinter):

```bash
python site_checker.py
```

## Four-column Excel report

Results are saved beside the input as `your_urls_checked.csv`.

| URL | Detailed response | Short result | IP address |
| --- | --- | --- | --- |
| example.com | 200 OK: Request fulfilled, document follows; requested/final URL, elapsed time, UTC timestamp | 200 | 192.0.2.10 |
| https://example.com/private | 403 Forbidden: Request forbidden; requested/final URL, elapsed time, UTC timestamp | 403 | 192.0.2.10 |
| https://example.com/old | Final HTTP response, requested/final URL, full redirect chain, elapsed time, UTC timestamp | transfer to https://example.com/new (200) | 192.0.2.20 |
| unreachable.example | DNS_ERROR and error details, requested URL, elapsed time, UTC timestamp | no response | unavailable |

These are illustrative examples, not live measurements. Any HTTP response produces its numeric status (including 404 and 503). Redirects include their destination and final status in the short result. If the destination fails to respond, the short result includes the destination and `no response`. Malformed URLs say `invalid URL`.

The **IP address** column lists unique IPv4 and IPv6 addresses resolved for the final destination hostname (or the original hostname when there is no redirect). Multiple addresses are separated by semicolons inside the cell. Failed lookups and invalid URLs show `unavailable`; an HTTP connection failure may still have resolved addresses. These are DNS lookup results, which can differ from the actual server used because of load balancing or proxies. DNS lookup time is included in the elapsed time.

Open the report in Excel, select its four columns, and press **Ctrl+T** (or **Insert → Table**). Enable **My table has headers**. Use **Wrap Text** on the detailed response column. Save as `.xlsx` to retain table formatting: CSV stores values only.

The report uses UTF-8 with BOM and a first-line `sep=,` hint so desktop Excel can recognize the delimiter across regional settings. For semicolons:

```bash
python site_checker.py your_urls.csv --delimiter semicolon
```

When importing through Excel's **Data → From Text/CSV**, choose the separator and skip the first `sep=` row before promoting headers if necessary. Other CSV readers should also skip that metadata row. Formula-like cell values are prefixed with an apostrophe for Excel.

## Input and options

Input is UTF-8 CSV, optionally with a header named `url`, `urls`, `website`, `site`, or `domain`. Otherwise the first column is used, including its first row. Comma, semicolon, and tab separators are detected. Blank URL cells are skipped; order and duplicates are preserved.

```bash
python site_checker.py urls.csv --column website --workers 5 --timeout 20 -o results.csv
```

Bare domains use HTTPS. To check HTTP explicitly, include `http://`. Certificates are verified. Checks use GET, follow redirects, and close after headers without downloading full pages. No automatic retries or fallback to HTTP. The timeout is per socket operation, not a strict overall deadline; DNS and redirects may add time.

404 means that page was not found; 403 may indicate access restrictions or bot blocking. A site returning an HTTP error is still responding. Results reflect the checking machine's network. JavaScript redirects and error pages served with status 200 are not detected. Reduce `--workers` if sites return rate limits.
