# KSU coursework web crawler

CS7263 PA1 — Akash Bharati (netid `abharati`, GitHub `AkashB142`).
Python 3.11.6. Both crawl and offline analysis stages are implemented.

## Install and run (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe src/crawler.py --budget 20 --output artifacts/smoke
.\.venv\Scripts\python.exe src/crawler.py --budget 500
.\.venv\Scripts\python.exe src/analyze.py --artifacts artifacts --output docs/analysis.md --seed 42 --near-threshold 0.8
```

Default seeds: `https://www.kennesaw.edu/` and
`https://www.kennesaw.edu/ccse/`. Override with `--seeds URL URL`.
Other options include `--delay 1`, `--timeout 20`, `--max-bytes 2000000`,
`--max-redirects 8`, `--user-agent KSU-Coursework-Crawler/1.0`, and `--output artifacts`.

The completed run used `.\.venv\Scripts\python.exe src/crawler.py --budget 500`
with the default seeds and settings. It stored 500 distinct HTTP-200 page URLs
in 582.735 seconds (9 minutes 42.735 seconds), October 11, 2026,
10:25:19–10:35:02 PM EDT. The analysis and follow-up probes were completed
October 12, after the October 11 11:59 PM deadline; no historical dates were changed.

Run the analysis command above against the saved local corpus; it does not make
network requests or alter crawl outputs. It generates all tables, the embedded
Zipf plot and Q1–Q8 answers in `docs/analysis.md`. Dated qualitative/live probe
evidence lives in `src/evidence.py` and is included in the report. Changing the
seed or near-duplicate threshold changes relevant results. A fresh checkout
must first run the crawler because the corpus is deliberately not committed;
a later live crawl can produce different results as websites change.

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

Analysis uses repeated normalized lines occurring on at least half of a host's
pages (minimum ten pages per host) to estimate boilerplate. It performs raw
five-word Jaccard near-duplicate screening at 0.8, response/text hash censuses,
canonical-link checks, corpus link counts, alphabetic word tokenization, a fixed
English stopword list, log-rank Zipf fitting and smoothed TF-IDF. A separate
paragraph-length filter demonstrates a keyword fix. No additional dependencies
beyond the pinned crawl libraries are required for analysis.

Known run limitations: four stored pages contain empty text; robots.txt
redirects were conservatively blocked rather than followed. The logged delay
audit does not strictly pass on every host (minimum approximately 0.986 seconds).
See Q8 for exact counts and the scheduling/logging diagnosis. Sequential
requests still limit concurrency to one globally. There are no per-pattern
trap limits beyond the overall budget. These are disclosed findings, not
claims that the original run met every requirement.

## Members and contributions

Akash Bharati — netid `abharati`; GitHub `AkashB142`; working individually.
Akash directed the crawler and analysis work using Codex, selected the crawl
scope, and ran the 500-page crawl. Codex generated implementation and report
material, ran checks and inspected corpus samples; assistance and verification
are recorded in `docs/ai_log.md`. Akash must review the code, findings and
limitations and be able to explain them during the presentation.

Private repository: [cs7263-pa1-abharati](https://github.com/AkashB142/cs7263-pa1-abharati).
GitHub verified the repository is private and the existing invitation to
`Jiho-YesNLP` is pending as of October 12. The instructor must accept it to read
the repository. The repository name was corrected to the required format.
The presentation occurs in the class session after submission; slides are optional.
