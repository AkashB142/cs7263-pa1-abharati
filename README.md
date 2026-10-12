# KSU coursework web crawler

Python 3.11.6. This repository currently implements the crawl stage; the separate
analysis stage and `docs/analysis.md` still need to be built.

## Install and run (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe src/crawler.py --budget 20 --output artifacts/smoke
.\.venv\Scripts\python.exe src/crawler.py --budget 500
```

Default seeds: `https://www.kennesaw.edu/` and
`https://www.kennesaw.edu/ccse/`. Override with `--seeds URL URL`.
Other options include `--delay 1`, `--timeout 20`, `--max-bytes 2000000`,
`--max-redirects 8`, `--user-agent KSU-Coursework-Crawler/1.0`, and `--output artifacts`.

Each run **overwrites** the three output files in its selected output directory.
Use different directories to preserve previous runs. There is no resume support.
Ctrl+C preserves completed records and writes partial-run statistics.
Exit status 1 means the crawl stopped before reaching its page budget.

## Architecture and policies

A FIFO queue and canonical URL set implement breadth-first traversal.
Only HTTP(S) URLs on `kennesaw.edu` or its subdomains enter the queue.
URL identity lowercases scheme/host, removes default ports/fragments, normalizes
percent escapes, decodes unreserved characters, and resolves dot segments.
Query parameters (including order and values) are preserved; trailing slashes
are preserved because either can affect server behavior. Crawl-trap limits
beyond the overall page budget are not yet implemented.

Requests are sequential, with at least one second between request starts to
the same hostname, including robots and redirect requests. Protego reads cached
robots policies once per origin (scheme/authority); longer Crawl-delay values
increase the host delay. Missing robots files allow crawling; robots network,
redirect, rate-limit, or server failures conservatively block that origin.
HTTP redirects are followed manually with scope/robots checks and loop limits.
HTML base links and canonical declarations are extracted; meta refresh targets
are queued and logged. Non-HTML and oversized bodies are recorded as failures.
There are no automatic retries.

`artifacts/pages.jsonl` stores raw extracted text, links, text SHA-256, and an
additional response SHA-256 for byte-identical duplicate analysis. No navigation
or footer removal happens at crawl time. `crawl.log` is JSONL and includes
request-start timestamps, decisions, stored-page records, and cached robots text.
`stats.json` records counts, seeds, delays, and measured runtime. Runtime is not
claimed until a run completes; read `wall_clock_seconds` from that run's stats.
Commit `crawl.log` and `stats.json` from the final run, but never `pages.jsonl`.

## Members and contributions

Akash — netid and GitHub username: to be completed by the student.
Akash directed the initial crawler implementation with AI assistance; final
contributions and verification should be updated as work proceeds.
