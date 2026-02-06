from lxml import etree as ET
import re

ROOT: ET.Element = None
def extract_metadata(html: ET.Element):
    global ROOT; ROOT = _html_to_ET(html)
    canonical_url = language = site = content_type = None
    title = _get_title()
    url = _get_url() or _get_og_url()
    language = _get_language()
    site = _get_site()
    canonical_url = _get_canonical_url(url)
    doc_id = _make_doc_id(canonical_url) if canonical_url else _make_doc_id(title)
    domain = _get_domain(canonical_url)
    fetched_at = _get_fetched_at()
    content_type = _get_content_type()
    
    out: dict[str, any] = {
        'id': f'{doc_id}::c',
        'text': '',
        'metadata': {
            'headings': [{}],
            'chunk_index': -1,
            'word_count' : -1,
            'start_char' : -1,
            'end_char' : -1,
            'overlap_char' : -1,
            'content_type' : content_type,
            'content_hash' : '',
            'url': url,
            'canonical_url': canonical_url,
            'title' : title,
            'site': site,
            'domain' : domain,
            'language' : language,
            'fetched_at' : fetched_at,
            'doc_id': doc_id,
        }
    }

    return out

def _html_to_ET(html: str) -> ET.Element:
    '''creates a correct working lxml tree'''
    import html5lib
    doc = html5lib.parse(html, treebuilder='lxml', namespaceHTMLElements=False)  # parse HTML
    return doc.getroot()

def _get_title() -> str | None:
    for title in ROOT.iter('title'):
        if title.text and title.text.strip(): return title.text.strip()
    for meta in ROOT.iter('meta'):
        if (meta.attrib.get('property') or '').lower() == 'og:title': return meta.attrib.get('content')
def _get_url() -> str | None:
    for child in ROOT.xpath('/comment()'):
        comment_text = (child.text or '').strip()
        m = re.search(r'saved from url=\(\d+\)(\S+)', comment_text)
        if m: return m.group(1)
def _get_og_url() -> str | None:
    for meta in ROOT.iter('meta'):
        if (meta.attrib.get('property') or '').lower() == 'og:url': return meta.attrib.get('content')
def _get_canonical_url(url: str) -> str | None:
    from urllib.parse import urljoin
    canonical_url = None
    for link in ROOT.iter('link'):
        rel = (link.attrib.get('rel') or '').lower().split()
        if 'canonical' in rel: 
            canonical_url = link.attrib.get('href')
            break
    if canonical_url: 
        return urljoin(url, canonical_url) if url else canonical_url
    return url
def _make_doc_id(url: str) -> str | None:
    import hashlib
    if url is None: return None
    url = url.lower().strip()
    if url.endswith('/') and url != '/': url = url[:-1]
    return hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]  # creates deterministic hash-id from URL
def _get_language() -> str | None:
    return ROOT.attrib.get('lang')
def _get_domain(url: str) -> str | None:
    if not url: return None
    from urllib.parse import urlparse
    host = urlparse(url).hostname
    return host.lower() if host else None
def _get_site() -> str | None:
    for meta in ROOT.iter('meta'):
        if (meta.attrib.get('property') or '').lower() == 'og:site_name': return meta.attrib.get('content')
    for link in ROOT.iter('link'):
        rel = (link.attrib.get("rel") or "").lower().split()
        if 'search' in rel: return link.attrib.get('title')
def _get_fetched_at() -> str | None:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
def _get_content_type() -> str | None:
    for meta in ROOT.iter('meta'):
        if 'charset' in meta.attrib: return f'charset={meta.attrib.get("charset")}'
        if (meta.attrib.get('http-equiv') or '').lower() == "content-type": return meta.attrib.get('content')