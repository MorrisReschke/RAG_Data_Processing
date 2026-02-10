from collections import Counter
import re

def extract_urls(metadata: dict[dict[str]], html: str) -> list[tuple[str, int]]:
    hrefs: list[str] = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.I)
    domain = metadata.get('domain')
    out = []
    for h in hrefs:
        if h.startswith('#'): continue
        if h.endswith('png') or h.endswith('css'): continue
        
        if h.startswith('//'): h = 'https:' + h
        if h.startswith('/'): h = 'https://' + domain + h
        out.append(h)
    return Counter(out).most_common()