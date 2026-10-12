# AI assistance log

## October 11, 2026 — Akash

Requested an explanation of the assignment and a Python crawler. Codex generated
the initial crawler, URL normalization module, URL tests, dependency list, and
run instructions. The design uses a FIFO frontier, sequential HTTP requests,
Protego robots policies, and separate raw text storage for later analysis.
Verification results are recorded below after execution. The student must review
and understand the implementation before submission.

Verification: four URL normalization/scope tests passed on Python 3.11.6.
A live five-page smoke crawl completed successfully, including an HTTP redirect
from the CCSE seed to campus.kennesaw.edu. JSONL schema and per-host request
timestamp gaps were checked. This does not establish completion of the required
500-page crawl or the analysis stage.

## October 12, 2026 — Akash

Akash requested completion of the analysis and remaining repository materials,
excluding slides, and supplied netid abharati and course CS7263. Codex verified
the completed October 11 crawl: 500 parseable records, 500 unique URLs, all HTTP
200, matching stored log events and stats; four records had empty extracted text.

Codex generated src/analyze.py and src/evidence.py, computed Q1–Q8 from the
saved corpus, and generated docs/analysis.md. Methods include URL-shape counts,
response/text hash grouping, raw five-word Jaccard similarity, per-host repeated
line cleaning, link rankings, word frequencies, log-rank Zipf fitting, seeded
TF-IDF sampling, a paragraph-length keyword fix, and timestamp/robots audits.
The near-duplicate threshold was selected after checking 0.80, 0.90 and 0.95
results and inspecting the degree-program/endorsement pair; stricter thresholds
find no non-exact pair. Both the inclusive result and sensitivity are reported.

Codex inspected the five sampled raw/cleaned openings and identified residual
menus and source spelling artifacts in keywords. It made a few dated live
requests for extreme CCSE parameters and news pagination, and checked Program
Finder and LibGuides robots rules. These are follow-up probes, not original
crawl records; the original crawl files were left unchanged. The analysis
exposed sub-second logged gaps and conservative blocks after robots redirects;
these shortcomings are explicitly reported rather than retroactively hidden.

Reproduction commands and dependencies are in README.md. Verification includes
the URL tests, analysis helper tests, independent input/hash/count checks, and
regenerating the report to check deterministic output. Codex updated README
identity, contributions and run instructions. Akash must read the generated
analysis/code and independently understand and defend the results. Completion
of the analysis occurred after the stated deadline; no dates were backdated.
