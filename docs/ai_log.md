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
