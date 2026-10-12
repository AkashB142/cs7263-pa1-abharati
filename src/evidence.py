"""Human-reviewed observations from the saved corpus and October 12 live probes.

Live evidence is dated separately from the October 11 crawl and never included
in the original crawl's request counts. It is embedded in the generated report.
"""
MANUAL = """
### Q1 probe observations — October 12, 2026, 00:15–00:17 EDT

Follow-up requests used the coursework User-Agent, robots checks, sequential
transport and host delays. These requests are not part of the 500-page crawl.

| Probe URL | HTTP | Observed title |
| --- | --- | --- |
| https://campus.kennesaw.edu/colleges-departments/ccse/ | 200 | College of Computing and Software Engineering |
| https://campus.kennesaw.edu/colleges-departments/ccse/?page=999999 | 200 | College of Computing and Software Engineering |
| https://campus.kennesaw.edu/colleges-departments/ccse/?date=2099-12-31 | 200 | College of Computing and Software Engineering |
| https://www.kennesaw.edu/news/news-releases/campus-community.php?tags=campus%20and%20community&categories=news%20releases&p=999999 | 200 | Campus & Community - News |

The two invented parameters on the largest CCSE section returned the same title
and opening navigation as the baseline; their response hashes differed. This
suggests permissive query handling, not proven byte duplication or infinite
linked traversal. Arbitrary query acceptance could create unlimited URL
identities if such links were generated. The extreme news pagination request
also returned 200, so status alone does not bound the parameter. These finite
probes cannot prove infinitely many distinct meaningful pages. The actual
crawl spent 55/500 pages (11%) in CCSE and only 2/500 (0.4%) on all query URLs.
No per-pattern limiter was applied, and no harmful budget concentration was
observed in this sample; a later version should cap pagination and measure
content yield before dropping parameters that might select real content.

### Q2 inspected duplication

The byte-identical catalog pair is the directory URL and its index.php alias,
not two unrelated articles. The canonical CCSE pair likewise differs only by
explicit index.php. The raw near-duplicate pair (degrees-programs directory
versus endorsements/index.php) shares institutional navigation and degree
listing vocabulary; the endorsements page narrows the scope. At threshold
0.80 the measured Jaccard 0.8275 qualifies; at 0.90 it does not. We select 0.80
as a moderately inclusive screening threshold and report the stricter result
alongside it, rather than calling the pair identical content.

### Q5 and Q7 qualitative checks

Reviewed all five deterministic sample openings before/after cleaning. The
shared MyKSU/college navigation disappeared, while Italy's Montepulciano prose,
CAPS counseling descriptions, the portal's introductory paragraph, student
engagement's mission, and Staff Senate's representative purpose remained.
Local menus still survive. Short repeated phrases such as "Staff Senate" can
be removed even when meaningful; the longer senate mission survives. This
shows both the usefulness and the limitations of whole-line template removal.
The worst keyword example is the Campus Hub portal: rare directory wording and
the source typo "Stategic" are not good topic summaries. The implemented
paragraph-length keyword fix removes brief menu labels. It cannot turn a
multi-purpose portal into a focused article, so partial improvement is reported.

### Q8 genuine rule examples and conservative blocks

Live robots checks returned HTTP 200 on October 12 and agreed with these
run-time cached rules. Two examples from the original blocked decisions:

1. https://programfinder.kennesaw.edu/s/search.html?collection=kennesaw-program-finder-meta
   is blocked by `Disallow: /s/` under `User-agent: *`. The URL path starts with
   /s/; query parameters do not defeat that prefix. Source:
   [Program Finder robots.txt](https://programfinder.kennesaw.edu/robots.txt).
2. https://libguides.kennesaw.edu/copyright/ is blocked by `Disallow: /` under
   `User-agent: *` (with `Crawl-delay: 10`). The root prefix matches every path.
   Specific named bot groups do not apply to KSU-Coursework-Crawler/1.0. Source:
   [LibGuides robots.txt](https://libguides.kennesaw.edu/robots.txt).

Other cached deny-all rules were synthesized after robots redirects/TLS
failure; they must not be attributed to the publisher. The report distinguishes
these decisions from rules actually retrieved. The 500-page crawl finished
October 11 at 22:35 EDT, but the analysis and probes were completed October 12,
after the stated October 11 23:59 deadline. No dates or logs were backdated.
"""
