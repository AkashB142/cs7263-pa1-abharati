"""Sequential, polite KSU crawler. Run from the repository root."""
import argparse
from collections import Counter, deque
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from protego import Protego
from urls import canonicalize, in_scope

def utc():
    return datetime.now(timezone.utc).isoformat()

class Crawler:
    def __init__(self, args):
        self.args = args
        self.session = requests.Session()
        self.session.headers['User-Agent'] = args.user_agent
        self.frontier = deque()
        self.seen = set()
        self.stored = set()
        self.next_request = {}
        self.robots = {}
        self.delays = {}
        self.counts = Counter()
        self.output = Path(args.output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.log = (self.output / 'crawl.log').open('w', encoding='utf-8', buffering=1)
        self.pages = (self.output / 'pages.jsonl').open('w', encoding='utf-8', buffering=1)

    def record(self, event, url, reason=None, **extra):
        record = dict(ts=utc(), event=event, url=url, failure_reason=reason, **extra)
        self.log.write(json.dumps(record, ensure_ascii=False) + '\n')
        self.counts[event] += 1
        if reason:
            self.counts['reason:' + reason] += 1

    def enqueue(self, value, base=None):
        try:
            url = canonicalize(value, base)
        except (ValueError, UnicodeError):
            self.record('skip', value, 'invalid_url')
            return
        if not in_scope(url):
            self.record('skip', url, 'outside_scope')
        elif url in self.seen:
            self.record('skip', url, 'already_seen')
        else:
            self.seen.add(url)
            self.frontier.append(url)
            self.record('enqueue', url)

    def request(self, url, kind='page'):
        host = urlsplit(url).hostname
        wait = self.next_request.get(host, 0) - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self.next_request[host] = time.monotonic() + self.delays.get(host, self.args.delay)
        self.record('fetch', url, request_kind=kind)
        self.counts['requests'] += 1
        try:
            with self.session.get(url, allow_redirects=False, stream=True,
                                  timeout=self.args.timeout) as response:
                status, headers = response.status_code, dict(response.headers)
                body = bytearray()
                for chunk in response.iter_content(16384):
                    body.extend(chunk)
                    if len(body) > self.args.max_bytes:
                        self.record('error', url, 'oversized_response', status=status)
                        return None
                return status, headers, bytes(body)
        except requests.exceptions.SSLError:
            reason = 'tls_error'
        except requests.exceptions.Timeout:
            reason = 'timeout'
        except requests.exceptions.ConnectionError:
            reason = 'connection_error'
        except requests.exceptions.RequestException:
            reason = 'request_error'
        self.record('error', url, reason)
        return None

    def allowed(self, url):
        parts = urlsplit(url)
        origin = urlunsplit((parts.scheme, parts.netloc, '', '', ''))
        host = parts.hostname
        if origin not in self.robots:
            robots_url = origin + '/robots.txt'
            result = self.request(robots_url, 'robots')
            # Conservative on network/server failures. Missing robots allows access.
            policy = 'User-agent: *\nDisallow: /'
            if result:
                status, headers, body = result
                if 200 <= status < 300:
                    policy = body.decode('utf-8', errors='replace')
                elif 400 <= status < 500 and status != 429:
                    policy = ''
                else:
                    self.record('error', robots_url, 'robots_unavailable', status=status)
            parser = Protego.parse(policy)
            delay = parser.crawl_delay(self.args.user_agent) or 0
            self.delays[host] = max(self.delays.get(host, self.args.delay), float(delay))
            self.next_request[host] = max(self.next_request.get(host, 0), time.monotonic() + self.delays[host])
            self.robots[origin] = parser
            self.record('robots_policy', robots_url, policy=policy, effective_delay=self.delays[host])
        if not self.robots[origin].can_fetch(url, self.args.user_agent):
            self.record('skip', url, 'robots_disallowed', host=host)
            return False
        return True

    def fetch_page(self, initial):
        url, chain = initial, set()
        for hop in range(self.args.max_redirects + 1):
            if url in chain:
                self.record('error', url, 'redirect_loop')
                return
            chain.add(url)
            if not self.allowed(url):
                return
            result = self.request(url)
            if result is None:
                return
            status, headers, body = result
            if 300 <= status < 400:
                location = headers.get('Location')
                if not location:
                    self.record('error', url, 'redirect_missing_location', status=status)
                    return
                if hop == self.args.max_redirects:
                    self.record('error', url, 'redirect_limit', status=status)
                    return
                try:
                    target = canonicalize(location, url)
                except (ValueError, UnicodeError):
                    self.record('error', url, 'invalid_redirect', status=status)
                    return
                self.record('redirect', url, status=status, target=target)
                if not in_scope(target):
                    self.record('skip', target, 'redirect_outside_scope')
                    return
                url = target
                if url in self.stored:
                    self.record('skip', url, 'redirect_already_stored')
                    return
                self.seen.add(url)
                continue
            if not 200 <= status < 300:
                self.record('error', url, f'http_{status}', status=status)
                return
            content_type = headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
                self.record('error', url, 'non_html', status=status, content_type=content_type)
                return
            try:
                soup = BeautifulSoup(body, 'html.parser')
                title = soup.title.get_text(' ', strip=True) if soup.title else ''
                base_tag = soup.find('base', href=True)
                base = canonicalize(base_tag['href'], url) if base_tag else url
                declared = soup.find('link', rel=lambda value: value and 'canonical' in value)
                canonical_link = canonicalize(declared['href'], base) if declared and declared.get('href') else None
                links = set()
                for tag in soup.find_all('a', href=True):
                    try:
                        link = canonicalize(tag['href'], base)
                        if in_scope(link):
                            links.add(link)
                        self.enqueue(tag['href'], base)
                    except (ValueError, UnicodeError):
                        self.record('skip', str(tag['href']), 'invalid_url')
                refresh = soup.find('meta', attrs={'http-equiv': re.compile('^refresh$', re.I)})
                if refresh:
                    match = re.search(r'url\s*=\s*(.+)', refresh.get('content', ''), re.I)
                    self.record('notice', url, 'meta_refresh')
                    if match:
                        self.enqueue(match.group(1).strip(" '\""), base)
                for tag in soup(['script', 'style', 'noscript', 'template']):
                    tag.decompose()
                text = soup.get_text('\n', strip=True)
                normalized = ' '.join(text.lower().split())
                page = dict(url_canonical=url, status=status, fetched_at=utc(), title=title,
                            text=text, word_count=len(re.findall(r'\b\w+\b', text)),
                            out_links=sorted(links), content_hash=hashlib.sha256(normalized.encode()).hexdigest(),
                            response_hash=hashlib.sha256(body).hexdigest(), canonical_link=canonical_link)
                self.pages.write(json.dumps(page, ensure_ascii=False) + '\n')
                self.stored.add(url)
                self.record('stored', url, status=status, word_count=page['word_count'])
                print(f'[{len(self.stored)}/{self.args.budget}] {url}', flush=True)
            except Exception as error:
                self.record('error', url, 'parse_error', detail=str(error))
            return

    def run(self):
        started, start_ts = time.monotonic(), utc()
        interrupted = False
        try:
            for seed in self.args.seeds:
                self.enqueue(seed)
            while self.frontier and len(self.stored) < self.args.budget:
                url = self.frontier.popleft()
                if url not in self.stored:
                    self.fetch_page(url)
        except KeyboardInterrupt:
            interrupted = True
            print('\nInterrupted; collected pages and logs retained.')
        finally:
            elapsed = time.monotonic() - started
            stats = dict(pages_fetched=len(self.stored), urls_seen=len(self.seen),
                         wall_clock_seconds=elapsed, started_at=start_ts, finished_at=utc(),
                         robots_skips=self.counts['reason:robots_disallowed'], random_seed=42,
                         request_count=self.counts['requests'], seeds=self.args.seeds,
                         page_budget=self.args.budget, delay=self.args.delay, host_delays=self.delays,
                         frontier_remaining=len(self.frontier), interrupted=interrupted,
                         counters=dict(self.counts), user_agent=self.args.user_agent)
            (self.output / 'stats.json').write_text(json.dumps(stats, indent=2), encoding='utf-8')
            self.pages.close()
            self.log.close()
            self.session.close()
        return 0 if len(self.stored) >= self.args.budget else 1

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', nargs='+', default=['https://www.kennesaw.edu/', 'https://www.kennesaw.edu/ccse/'])
    parser.add_argument('--budget', type=int, default=500)
    parser.add_argument('--delay', type=float, default=1.0)
    parser.add_argument('--timeout', type=float, default=20)
    parser.add_argument('--max-bytes', type=int, default=2_000_000)
    parser.add_argument('--max-redirects', type=int, default=8)
    parser.add_argument('--user-agent', default='KSU-Coursework-Crawler/1.0')
    parser.add_argument('--output', default='artifacts')
    args = parser.parse_args()
    if args.budget < 1 or args.delay < 1 or args.timeout <= 0 or args.max_bytes < 1 or args.max_redirects < 0:
        parser.error('budget/timeout/byte cap must be positive; delay >= 1; redirects >= 0')
    if any(not in_scope(canonicalize(seed)) for seed in args.seeds):
        parser.error('all seeds must be within kennesaw.edu')
    raise SystemExit(Crawler(args).run())

if __name__ == '__main__':
    main()
