from urllib.parse import urljoin, urlparse, urldefrag
from html import unescape
from collections import Counter
import re

def extract_urls(domain: str, canonical_url: str, html: str) -> list[tuple[str, int]]:
    hrefs: list[str] = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.I)
    suffix = re.search(rf'{re.escape(domain)}(.*)$', canonical_url).group(1)
    out = []
    for h in hrefs:
        if h.startswith('#'): continue
        if h.startswith('//'): h = 'https:' + h
        h = unescape(h)
        url = urljoin(canonical_url, h)
        url, _ = urldefrag(url)
        p = urlparse(url)
        if p.scheme not in ('http', 'https'): continue
        if 'edit' in p.query: continue
        if h.endswith(suffix): continue
        if canonical_url in url: continue
        out.append(url)
    return Counter(out).most_common()