"""URL identity and scope rules shared by the crawler."""
import re
from urllib.parse import urlsplit, urlunsplit, urljoin

UNRESERVED = frozenset('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~')

def normalize_encoding(value):
    def replace(match):
        character = chr(int(match.group(1), 16))
        return character if character in UNRESERVED else '%' + match.group(1).upper()
    return re.sub(r'%([0-9a-fA-F]{2})', replace, value)

def canonicalize(url, base=None):
    """Preserve queries and trailing slashes; normalize RFC 3986 identity parts."""
    parts = urlsplit(urljoin(base, url) if base else url)
    scheme = parts.scheme.lower()
    if scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise ValueError('unsupported_url')
    host = parts.hostname.lower().encode('idna').decode('ascii')
    port = parts.port
    authority = host + (f':{port}' if port and (scheme, port) not in [('http', 80), ('https', 443)] else '')
    path = normalize_encoding(parts.path or '/')
    # RFC 3986 remove_dot_segments, preserving repeated and trailing slashes.
    remaining, output = path, ''
    while remaining:
        if remaining.startswith('../'):
            remaining = remaining[3:]
        elif remaining.startswith('./'):
            remaining = remaining[2:]
        elif remaining.startswith('/./') or remaining == '/.':
            remaining = '/' + remaining[3:]
        elif remaining.startswith('/../') or remaining == '/..':
            remaining = '/' + remaining[4:]
            output = output.rsplit('/', 1)[0]
        elif remaining in ('.', '..'):
            remaining = ''
        else:
            end = remaining.find('/', 1 if remaining.startswith('/') else 0)
            if end == -1:
                output += remaining
                remaining = ''
            else:
                output += remaining[:end]
                remaining = remaining[end:]
    return urlunsplit((scheme, authority, output or '/', normalize_encoding(parts.query), ''))

def in_scope(url):
    host = urlsplit(url).hostname or ''
    return host == 'kennesaw.edu' or host.endswith('.kennesaw.edu')
