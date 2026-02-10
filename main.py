from src.extract_text import process_multiple_docs, download_html, Doc
from src.extract_text_via_bs4 import extract_text_via_bs4
from src.extract_metadata import extract_metadata
from src.extract_urls import extract_urls
from src.chunking import chunking
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[0]
SILENT = True

def run_pipeline():  # main pipeline runner (loops over getURLs.txt)
    for url in _get_urls_to_process():  # process each line in getURLs.txt
        if not url: continue  # skip empty lines
        html, title = download_html(url, ROOT)  # download base page (no disk writes; Abort safe)
        chunk_template = extract_metadata(html)  # extract base metadata (canonical/url/domain/etc)
        metadata = chunk_template.get('metadata')
        extracted_urls = extract_urls(metadata, html)  # extract candidate URLs as list[(url,count)]
        docs: list[Doc] = process_multiple_docs(url, html, title, extracted_urls, chunk_template, ROOT, SILENT)  # open GUI for THIS base URL and return chosen docs
        for doc in docs:  # write only after OK (Abort returns empty list)
            Path(f'{ROOT}/data/{doc.title}').mkdir(parents=True, exist_ok=True)  # create per-doc folder
            _write_raw(doc.title, doc.html)
            _write_input(doc.title, doc.html)  # write raw html input
            _write_output(doc.title, doc.text)  # write rendered plaintext output
            chunks = chunking(doc.text, doc.metadata)  # chunk the text for RAG (uses markers)
            _write_chunks(doc.title, chunks)  # write jsonl chunks
        text = extract_text_via_bs4(html)
        Path(f'{ROOT}/data/BS4 {title}').mkdir(parents=True, exist_ok=True)  # create per-doc folder
        _write_output(f'BS4 {title}', text)
            
def _get_urls_to_process() -> list[str]:
        url_path = f'{ROOT}/config/getURLs.txt'
        urls: list[str] = []
        with open(url_path, 'r', encoding='utf-8') as f:
            for ln in f.read().split('\n'): urls.append(ln.strip())
        return urls

def _write_raw(title: str, html: str):
    raw_path = f'{ROOT}/data/{title}/{title}_raw.html'
    with open(raw_path, 'w', encoding='utf-8') as f:
        f.write(html)
        print(f'RAW: "{title}" has been written')

def _write_input(title: str, html: str):
    input_path = f'{ROOT}/data/{title}/{title}_input.txt'
    with open(input_path, 'w', encoding='utf-8') as f:
        f.write(html)
        print(f'Input: "{title}" has been written')

def _write_output(title, text: str):
    output_path = f'{ROOT}/data/{title}/{title}_output.txt'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)
        print(f'Output: "{title}" has been written')
    
def _write_chunks(title: str, text: list[dict[str, any]]):
    chunk_path = f'{ROOT}/data/{title}/{title}_chunks.jsonl'
    with open(chunk_path, 'w', encoding='utf-8') as f:
        for txt in text: f.write(json.dumps(txt, ensure_ascii=False) + '\n')
        print(f'Chunks: "{title}" has been written')
        
run_pipeline()