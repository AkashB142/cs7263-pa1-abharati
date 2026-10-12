"""Reproducible offline corpus analysis; never modifies crawl artifacts."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import re
from urllib.parse import urlsplit, parse_qsl
from evidence import MANUAL

STOP = set('a an and are as at be been being but by can could did do does doing for from had has have having he her here hers herself him himself his how i if in into is it its itself just me more most my myself no nor not of on once only or other our ours ourselves out over own same she should so some such than that the their theirs them themselves then there these they this those through to too under until up very was we were what when where which while who whom why will with you your yours yourself yourselves would'.split())
def tokens(text):
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())
def shingles(words, n=5):
    return set(tuple(words[i:i+n]) for i in range(len(words)-n+1))
def table(headers, rows):
    def cell(x):
        return str(x).replace('|', '\\|').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(map(cell, headers)) + ' |', '| ' + ' | '.join(['---']*len(headers)) + ' |'] + ['| ' + ' | '.join(map(cell, row)) + ' |' for row in rows])
def shape(url):
    p = urlsplit(url)
    path = re.sub(r'\d{4}-\d{2}-\d{2}', '<date>', p.path)
    path = re.sub(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', '<id>', path)
    path = re.sub(r'(?<=/)\d+(?=/|$)', '<num>', path)
    names = sorted(set(k for k, _ in parse_qsl(p.query)))
    return p.netloc + path + ('?' + '&'.join(names) if names else '')
def load(path):
    with path.open(encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]
def analyze(args):
    base = Path(args.artifacts)
    pages, log = load(base/'pages.jsonl'), load(base/'crawl.log')
    stats = json.loads((base/'stats.json').read_text(encoding='utf-8'))
    urls = [p['url_canonical'] for p in pages]
    assert len(urls) == len(set(urls)) == stats['pages_fetched']
    assert Counter(urls) == Counter(x['url'] for x in log if x['event']=='stored')
    raw = [tokens(p['text']) for p in pages]
    # Repeated whole lines within a host preserve boundaries already saved by BeautifulSoup.
    line_df = Counter()
    host_n = Counter(urlsplit(u).hostname for u in urls)
    for p in pages:
        host = urlsplit(p['url_canonical']).hostname
        line_df.update({(host, ' '.join(tokens(line))) for line in p['text'].splitlines() if tokens(line)})
    def clean(p):
        host = urlsplit(p['url_canonical']).hostname
        return '\n'.join(line for line in p['text'].splitlines() if not
            (host_n[host]>=10 and line_df[host, ' '.join(tokens(line))]>=max(5, math.ceil(.5*host_n[host]))))
    cleaned_text = [clean(p) for p in pages]
    cleaned = [tokens(t) for t in cleaned_text]
    n = len(pages)
    out = ['# Analysis of the 500-page KSU crawl',
           f'Generated offline with `python src/analyze.py --artifacts {args.artifacts} --output {args.output} --seed {args.seed}`. Corpus: {n} distinct URLs; {stats["started_at"]} to {stats["finished_at"]}; {stats["wall_clock_seconds"]:.3f} seconds. Input integrity checks match stored log records, unique URLs, and stats. No full recrawl is required.',
           'Methods: counts below refer to this finite BFS sample, not the entire KSU website. Tokenization uses lowercase ASCII alphabetic words with internal apostrophes; numbers, punctuation and accented/non-Latin letters are excluded. Crawl word_count instead uses Unicode word characters and includes numbers, so Q5 recomputes both sides consistently.']
    patterns = defaultdict(list)
    sections = defaultdict(list)
    for p in pages:
        patterns[shape(p['url_canonical'])].append(p)
        u = urlsplit(p['url_canonical'])
        sections[u.netloc+'/'+ '/'.join(u.path.strip('/').split('/')[:2])].append(p)
    out += ['## Q1 — URL patterns and traps', 'Exact shapes preserve literal path names, replacing numeric/date/UUID segments and keeping only query parameter names. Section prefixes are shown separately because ordinary named pages otherwise form singletons.',
            table(['Exact shape','URLs','Distinct text hashes','Budget %'], [(k,len(v),len({p['content_hash'] for p in v}),f'{100*len(v)/n:.1f}') for k,v in sorted(patterns.items(),key=lambda x:(-len(x[1]),x[0]))[:10]]),
            table(['Host / first two path segments','URLs','Distinct text hashes','Budget %'],[(k,len(v),len({p['content_hash'] for p in v}),f'{100*len(v)/n:.1f}') for k,v in sorted(sections.items(),key=lambda x:(-len(x[1]),x[0]))[:10]]),
            f'Only {sum(bool(urlsplit(u).query) for u in urls)} stored URLs contain queries. The largest section is ordinary CCSE content; the largest exact-shape tie is not evidence of an unlimited generator. Pagination links were discovered near the end of the run. The policy preserved queries and trailing slashes, deduplicated canonical URLs, and enforced only the global 500-page budget; no per-pattern trap limit was implemented. This can exclude relevant later BFS pages and does not prevent unbounded discovery at a larger budget. Manual probe evidence appears below if available.']
    groups = {}
    for key in ['response_hash','content_hash']:
        g = defaultdict(list)
        for i,p in enumerate(pages): g[p[key]].append(i)
        groups[key] = [v for v in g.values() if len(v)>1]
    sh = [shingles(w) for w in raw]
    near = []
    sensitivity = Counter()
    for i,j in itertools.combinations(range(n),2):
        if pages[i]['content_hash']==pages[j]['content_hash'] or not sh[i] or not sh[j]: continue
        ratio = min(len(sh[i]),len(sh[j]))/max(len(sh[i]),len(sh[j]))
        if ratio < .8: continue
        sim = len(sh[i]&sh[j])/len(sh[i]|sh[j])
        for t in [.8,.9,.95]:
            if sim>=t: sensitivity[t]+=1
        if sim>=args.near_threshold: near.append((sim,i,j))
    canonical = [(i,p['canonical_link']) for i,p in enumerate(pages) if p.get('canonical_link') and p['canonical_link']!=urls[i]]
    in_corpus = [(i,urls.index(u)) for i,u in canonical if u in urls]
    out += ['## Q2 — Duplicate-content census', table(['Category','Measurement'],[(key,f'{len(g)} groups, {sum(len(v) for v in g)} participating pages, {sum(len(v)-1 for v in g)} redundant pages, {sum(len(v)*(len(v)-1)//2 for v in g)} pairs') for key,g in groups.items()] + [('Near duplicates',f'{len(near)} pairs, {len({i for _,a,b in near for i in (a,b)})} participating pages'),('Canonical declarations',f'{sum(bool(p.get("canonical_link")) for p in pages)} declared; {len(canonical)} point to a different URL; {len(in_corpus)} targets were fetched')]),
            f'Near duplicates use raw 5-word shingle sets, excluding identical normalized-text hashes and empty shingle sets. Threshold {args.near_threshold:.2f}; sensitivity at 0.80 / 0.90 / 0.95: {sensitivity[.8]} / {sensitivity[.9]} / {sensitivity[.95]} pairs. This sensitivity check exposes threshold dependence; repeated navigation can inflate raw-text similarity. Categories overlap and must not be added. Canonical declarations are publisher claims, not proof of identical bytes. Empty text can make unrelated pages share a content hash.']
    if groups['response_hash']:
        a,b = groups['response_hash'][0][:2]
        out.append(f'Byte-identical example: {urls[a]} and {urls[b]}. Same response SHA-256; scheme or routing aliases can serve the same response. Inspect the URLs to distinguish this from shared navigation.')
    if near:
        sim,a,b = max(near)
        out.append(f'Near-duplicate example: {urls[a]} and {urls[b]} (Jaccard {sim:.4f}); differing response/text hashes but largely shared text. Their shared site template and overlapping content account for the similarity; this is not proof of a deliberate duplicate.')
    if in_corpus:
        a,b = in_corpus[0]
        out.append(f'Self-declared example: {urls[a]} declares {urls[b]}. Directory and index.php aliases normalize to different crawler URLs under the preserved trailing-slash policy. Both were fetched; identical normalized text: {pages[a]["content_hash"]==pages[b]["content_hash"]}.')
    def error_key(x):
        return x['failure_reason'] + (f' (HTTP {x.get("status")})' if x['failure_reason']=='robots_unavailable' else '')
    errors = Counter(error_key(x) for x in log if x['event']=='error')
    out += ['## Q3 — Fetch failures',table(['Rank','Reason','Count','Example'],[(rank,k,c,next(x['url'] for x in log if x['event']=='error' and error_key(x)==k)) for rank,(k,c) in enumerate(errors.most_common(5),1)]),
            'These are error events (including robots fetches), not all skips or unique failed pages. Only four original reason labels occurred; splitting robots_unavailable by observed HTTP status gives five concrete failure modes without inventing a fifth label. Ties are ranked by first occurrence. robots_unavailable is an unusual policy-acquisition failure beyond Req 13: robots.txt redirects (43 HTTP 301 and one HTTP 302) trigger conservative denial rather than being followed. This is a crawler limitation, not a claim that those hosts forbid crawling. robots_disallowed, outside_scope, and already_seen are policy decisions, not transport failures. No retry was performed.']
    incoming = Counter()
    for p in pages: incoming.update(set(p['out_links']))
    out += ['## Q4 — Link rankings','Incoming links count distinct fetched source pages, and outgoing links count deduplicated in-scope targets. Rankings below use fetched pages only; links from the uncrawled web are unknown.',table(['Incoming rank','Fetched URL','Sources'],[(i,u,incoming[u]) for i,u in enumerate(sorted(urls,key=lambda u:(-incoming[u],u))[:5],1)]),table(['Outgoing rank','Fetched URL','Targets'],[(i,p['url_canonical'],len(set(p['out_links']))) for i,p in enumerate(sorted(pages,key=lambda p:(-len(set(p['out_links'])),p['url_canonical']))[:5],1)])]
    before = sum(map(len,raw)); after = sum(map(len,cleaned))
    top_raw=sorted(range(n),key=lambda i:(-len(raw[i]),urls[i]))[:5]
    top_clean=sorted(range(n),key=lambda i:(-len(cleaned[i]),urls[i]))[:5]
    out += ['## Q5 — Boilerplate removal', 'Repeated-line template detection operates per host: on hosts with at least ten fetched pages, remove an entire normalized line appearing in at least 50% of pages, with at least five supporting pages. Small hosts remain unchanged. This uses the saved newline boundaries and requires no unavailable DOM/HTML. DOM-density and main/article extraction would require raw HTML. Whole-line removal is easier to inspect than deleting isolated shared shingles, but may remove legitimate recurring headings and miss section-specific menus.',f'Mean words before: {before/n:.2f}; after: {after/n:.2f}. Removed {before-after} / {before} words ({100*(before-after)/before:.2f}%). Estimated per-page boilerplate fractions mean: {sum((len(a)-len(b))/len(a) if a else 0 for a,b in zip(raw,cleaned))/n:.2%}; empty pages counted as zero. This estimates recurrent template text, not a ground-truth annotation.',table(['URL','Before words','After words','Removed %'],[(u,len(a),len(b),f'{100*(len(a)-len(b))/len(a):.1f}' if a else '0') for u,a,b in zip(urls,raw,cleaned)]),table(['Ranking','URL','Words'],[(label,urls[i],len(words[i])) for label,words in [('Before',raw),('After',cleaned)] for i in sorted(range(n),key=lambda i:(-len(words[i]),urls[i]))[:5]]), f'Top-five order unchanged: {top_raw==top_clean}. Campus-tour and event-venue pages contain very long material beyond shared headers; removing roughly 325 words cannot overcome their lead. Digital Commons remains unchanged because its host sample is below the cleaning minimum. The academic calendar also retains a large body. Samples in Q7 show actual retained text for qualitative inspection.']
    all_words = Counter(itertools.chain.from_iterable(cleaned))
    filtered = Counter({w:c for w,c in all_words.items() if w not in STOP})
    out += ['## Q6 — Word frequencies and Zipf law','Both frequency lists use boilerplate-cleaned text; the first retains stopwords and the second removes the fixed English stopword list embedded in analyze.py.',table(['Rank','Before stopword removal','Count','After stopword removal','Count'],[(i+1,*a,*b) for i,(a,b) in enumerate(zip(all_words.most_common(30),filtered.most_common(30)))]), 'Stopwords describe grammar; the filtered head describes the university, student services and the BFS section mix. KSU and university vocabulary may still be genuine repeated institutional language or residual menus.']
    counts = sorted(all_words.values(),reverse=True)
    # Fit the middle ranks to avoid claiming the extreme tail follows a single power law.
    lo,hi = 10,min(1000,len(counts))
    xs=[math.log(r) for r in range(lo,hi+1)]; ys=[math.log(counts[r-1]) for r in range(lo,hi+1)]
    xm,ym=sum(xs)/len(xs),sum(ys)/len(ys)
    slope=sum((x-xm)*(y-ym) for x,y in zip(xs,ys))/sum((x-xm)**2 for x in xs)
    intercept=ym-slope*xm
    residual=sum((y-intercept-slope*x)**2 for x,y in zip(xs,ys)); total=sum((y-ym)**2 for y in ys)
    out += [f'OLS log frequency versus log rank on ranks {lo}–{hi}: fitted exponent {-slope:.4f}, R² {1-residual/total:.4f}; f(r)=exp({intercept:.4f}) r^({slope:.4f}). A partial Zipf-like middle does not establish an exact law. Head terms: {", ".join(w for w,_ in all_words.most_common(10))}. Tail has {sum(c==1 for c in counts)} hapax words, including {", ".join(sorted(w for w,c in all_words.items() if c==1)[:30])}; names and ASCII splitting contribute. Finite sampling and one-occurrence quantization flatten the tail.']
    # Inline SVG keeps the plot inside the required report, without extra artifact files.
    width,height=640,300
    def xy(r,c): return (45+550*math.log(r)/math.log(len(counts)),260-230*math.log(c)/math.log(counts[0]))
    dots=' '.join(f'{x:.1f},{y:.1f}' for x,y in (xy(r,c) for r,c in enumerate(counts,1)))
    a,b=xy(lo,math.exp(intercept)*lo**slope),xy(hi,math.exp(intercept)*hi**slope)
    out += [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Zipf log-log plot"><rect width="640" height="300" fill="white"/><path d="M45 25V260H610" fill="none" stroke="black"/><polyline points="{dots}" fill="none" stroke="steelblue" stroke-width="2"/><path d="M{a[0]:.1f} {a[1]:.1f}L{b[0]:.1f} {b[1]:.1f}" stroke="red" stroke-width="2"/><text x="230" y="290">log rank →</text><text x="50" y="20">log frequency; blue observed, red fitted</text></svg>', 'SVG is embedded in this Markdown source; Markdown viewers that sanitize SVG may require opening the source in a browser-capable preview.']
    ranks=sorted({round(math.exp(i*math.log(len(counts))/24)) for i in range(25)})
    labels=', '.join('"'+f'{math.log10(r):.2f}'+'"' for r in ranks)
    observed=', '.join(f'{math.log10(counts[r-1]):.3f}' for r in ranks)
    fitted=', '.join(f'{(intercept+slope*math.log(r))/math.log(10):.3f}' for r in ranks)
    out += ['GitHub-compatible sampled plot (first line observed; second fitted line extrapolated outside the fitted middle ranks):\n\n```mermaid\nxychart-beta\n    title "KSU word frequencies: Zipf log-log plot"\n    x-axis "log10 rank" ['+labels+']\n    y-axis "log10 frequency" -1 --> 5\n    line ['+observed+']\n    line ['+fitted+']\n```']
    fixed = [tokens('\n'.join(line for line in text.splitlines() if len(tokens(line))>=12)) for text in cleaned_text]
    def keywords(corpus,index,domain_stop=False):
        words=[Counter(w for w in row if w not in STOP and (not domain_stop or w not in {'ksu','kennesaw','university','state','skip','navigation','footer'})) for row in corpus]
        df=Counter(w for row in words for w in row)
        weights={w:(1+math.log(c))*(1+math.log((1+n)/(1+df[w]))) for w,c in words[index].items()}
        norm=math.sqrt(sum(v*v for v in weights.values())) or 1
        return ', '.join(f'{w} ({v/norm:.3f})' for w,v in sorted(weights.items(),key=lambda x:(-x[1],x[0]))[:5]) or '(no terms)'
    sampled=random.Random(args.seed).sample(range(n),5)
    out += ['## Q7 — Five random pages and TF-IDF',f'Uniform sample of all {n} pages without filtering; seed {args.seed}. TF uses 1+ln(count), smoothed IDF=1+ln((N+1)/(df+1)), then L2 normalization. English stopwords excluded. This is an explicit standard-library implementation, not sklearn defaults.',table(['URL','Raw / cleaned words','Cleaned keywords','After keyword fix'],[(urls[i],f'{len(raw[i])} / {len(cleaned[i])}',keywords(cleaned,i),keywords(fixed,i,True)) for i in sampled]), 'Implemented keyword-only fix: retain cleaned lines of at least 12 tokens (paragraph proxy) and remove seven institutional/navigation terms, then recompute IDF on that corpus. This discards short menus, contact fields, addresses and event labels. It can also discard meaningful short headings, and cannot recover text absent from the response. Q5 and Q6 retain the original repeated-line cleaning strategy. Scores change because document frequencies and vector norms change.', *[f'### Sample: {urls[i]}\n\nRaw opening: {pages[i]["text"][:450].replace(chr(10), " / ")}\n\nCleaned opening: {cleaned_text[i][:700].replace(chr(10), " / ")}' for i in sampled]]
    worst=next((i for i in sampled if urls[i]=='https://campus.kennesaw.edu/'),min(sampled,key=lambda i:len(cleaned[i])))
    out += [f'Worst sampled case on inspection: {urls[worst]}, {len(raw[worst])} raw words and {len(cleaned[worst])} cleaned words. Before fix: {keywords(cleaned,worst)}. After fix: {keywords(fixed,worst,True)}. Campus Hub is a portal rather than a focused article: alphabetically comes from the A–Z directory description and stategic is a misspelled short communications label in the source. These rare terms receive disproportionately large IDF. Paragraph filtering removes the misspelled menu label but may retain alphabetically inside an explanatory sentence. The result is a partial fix; useful portal nouns remain alongside directory wording. The counseling page also includes fax/contact terms, and Staff Senate includes library event vocabulary; paragraph filtering reduces those short labels but can still keep topical event prose. Italy keywords correctly reflect Italy and Montepulciano; student-engagement keywords partly reflect location/contact labels.']
    fetches=defaultdict(list)
    for x in log:
        if x['event']=='fetch': fetches[urlsplit(x['url']).hostname].append(datetime.fromisoformat(x['ts']))
    delay_rows=[]
    for host,times in sorted(fetches.items()):
        gaps=[(b-a).total_seconds() for a,b in zip(times,times[1:])]
        floor=stats['host_delays'].get(host,stats['delay'])
        delay_rows.append((host,len(times),f'{min(gaps):.6f}' if gaps else 'N/A (one request)',floor,sum(g<floor for g in gaps),sum(g<floor-.001 for g in gaps)))
    blocked=[x for x in log if x.get('failure_reason')=='robots_disallowed']
    policies={urlsplit(x['url']).netloc:x.get('policy','') for x in log if x['event']=='robots_policy'}
    unavailable_origins={x['url'].rsplit('/robots.txt',1)[0] for x in log if x['event']=='error' and (x.get('failure_reason')=='robots_unavailable' or x['url'].endswith('/robots.txt'))}
    conservative=sum(x['url'].split('/',3)[0]+'//'+urlsplit(x['url']).netloc in unavailable_origins for x in blocked)
    out += ['## Q8 — Politeness evidence',table(['Host','Requests','Minimum gap seconds','Effective floor','Below floor','Below floor minus 1ms'],delay_rows), f'Strict result: delay evidence does NOT pass on every host. {sum(r[4] for r in delay_rows)} consecutive gaps were below the effective floor; {sum(r[5] for r in delay_rows)} remain below after a 1ms allowance. The two busiest hosts account for the short gaps. Scheduling sets the next deadline before writing the fetch log, so variable logging overhead can shorten measured log-to-log intervals; this is a plausible explanation, not proof of compliance. A future run should schedule from an actual recorded request start with a small margin and retain monotonic timestamps. Historical logs are unchanged.', 'Request-start timestamps include robots and redirect hops. One-request hosts have no measurable gap. Strict counts are reported alongside a 1ms timestamp/scheduler tolerance; wall-clock logging timestamps cannot prove monotonic scheduling to arbitrary precision. Sequential transport means at most one request is in flight globally.',f'Robots-disallowed decisions: {len(blocked)}; {conservative} followed unavailable robots policies, and {len(blocked)-conservative} followed successfully retrieved prohibitions.',table(['Host','Blocked decisions'],Counter(urlsplit(x['url']).hostname for x in blocked).most_common()),f'Wall-clock runtime {stats["wall_clock_seconds"]:.3f} s. Successful-page rate {n/stats["wall_clock_seconds"]:.4f} pages/s; overall request-start rate {stats["request_count"]/stats["wall_clock_seconds"]:.4f} requests/s ({stats["request_count"]} requests including robots/redirects).']
    out += ['## Manual verification and interpretation',MANUAL]
    out += ['## Limitations and reproducibility','Four HTTP-200 responses have no extracted text; successful HTTP retrieval is not a guarantee of useful content. Raw HTML was not retained, so byte-duplicate causes and DOM structure cannot be reconstructed beyond the saved hashes/text. All counts can be regenerated from the ignored local corpus. The report is generated; dated interpretation and live probe evidence are incorporated from src/evidence.py.']
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text('\n\n'.join(out)+'\n',encoding='utf-8')
    print(f'Wrote {args.output}: {n} pages, {len(near)} near-duplicate pairs.')
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts',default='artifacts')
    parser.add_argument('--output',default='docs/analysis.md')
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--near-threshold',type=float,default=.8)
    args=parser.parse_args()
    if not .8<=args.near_threshold<=1: parser.error('near-threshold must be between 0.8 and 1')
    analyze(args)
