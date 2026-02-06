from playwright.sync_api import sync_playwright
from src.html_to_text import html_to_text
from src.html_to_text import review_session, DocumentState, _html_to_ET  # NEW
from src.extract_metadata import extract_metadata
from src.extract_urls import extract_urls
from src.chunking import chunking
from pathlib import Path
import os, json, re  # CHANGED

ROOT = Path(__file__).resolve().parents[1]

def run_pipeline():
    urls = [u for u in _get_urls_to_process() if u]  # CHANGED
    if not urls:  # NEW
        return  # NEW

    for start_url in urls:  # NEW
        first_doc = _build_document_state_from_url(start_url)  # CHANGED
        docs = review_session([first_doc], load_doc_fn=_build_document_state_from_url)  # CHANGED

        for doc in docs:  # (unchanged, aber bleibt hier korrekt)
            base_name = doc.base_name
            Path(f'{ROOT}/data/{base_name}').mkdir(parents=True, exist_ok=True)
            _write_input(base_name, doc.html)
            _write_output(base_name, doc.final_text)
            out, base_name = chunking(doc.final_text, doc.metadata, base_name)
            _write_chunks(base_name, out)

            
def _get_urls_to_process() -> list[str]:
        url_path = f'{ROOT}/src/config/getURLs.txt'
        urls: list[str] = []
        with open(url_path, 'r', encoding='utf-8') as f:
            for ln in f.read().split('\n'):
                urls.append(ln.strip())
        return urls

def _sanitize_filename(name: str) -> str:  # NEW
    name = (name or '').strip()  # NEW
    name = re.sub(r'\s+', ' ', name)  # NEW
    name = re.sub(r'[^A-Za-z0-9._-]+', '_', name)  # NEW
    name = name.strip('._-')  # NEW
    return name or 'document'  # NEW

def _build_document_state_from_url(url: str) -> DocumentState:  # NEW
    title, html = _download_html(url)  # NEW
    metadata = extract_metadata(html)  # NEW
    canonical_url = metadata.get('metadata', {}).get('canonical_url')  # NEW
    domain = metadata.get('metadata', {}).get('domain')  # NEW
    urls_ranked = extract_urls(domain, canonical_url, html) if domain and canonical_url else []  # NEW
    root = _html_to_ET(html)  # NEW

    meta_title = metadata.get('metadata', {}).get('title')  # NEW
    doc_id = metadata.get('metadata', {}).get('doc_id')  # NEW
    base = _sanitize_filename(meta_title or title)  # NEW
    did = _sanitize_filename(doc_id or '')  # NEW
    base_name = f"{base}__{did}" if did else base  # NEW

    return DocumentState(  # NEW
        url_requested=url,  # NEW
        base_name=base_name,  # NEW
        html=html,  # NEW
        metadata=metadata,  # NEW
        canonical_url=canonical_url,  # NEW
        urls_ranked=urls_ranked,  # NEW
        root=root,  # NEW
    )  # NEW
    
def _download_html(url: str):  # CHANGED
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        title = page.title()
        html = page.content()
        browser.close()

    safe = _sanitize_filename(title)  # NEW
    with open(f'{ROOT}/data/{safe}.html', 'w', encoding='utf-8') as f:  # CHANGED
        f.write(html)
        print(f'RAW: "{title}" has been written')

    return title, html  # NEW

def _load_html_files():
    raw_path = Path(f'{ROOT}/data')
    for path in raw_path.glob("*.html"):  
        with path.open('r', encoding='utf-8') as file:
            content = file.read()
        yield path.name, content

def _write_input(base_name: str, html: str):
    input_path = f'{ROOT}/data/{base_name}/{base_name}_input.txt'
    with open(input_path, 'w', encoding='utf-8') as f:
        f.write(html)
        print(f'Input: "{base_name}" has been written')

def _write_output(base_name, text: str):
    output_path = f'{ROOT}/data/{base_name}/{base_name}_output.txt'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)
        print(f'Output: "{base_name}" has been written')
    
def _write_chunks(base_name: str, text: list[dict[str, any]]):
    chunk_path = f'{ROOT}/data/{base_name}/{base_name}_chunks.jsonl'
    with open(chunk_path, 'w', encoding='utf-8') as f:
        for txt in text: f.write(json.dumps(txt, ensure_ascii=False) + '\n')
        print(f'Chunks: "{base_name}" has been written')
        
run_pipeline()
