from src.filters.filter_attribute import *  # Attribute-based filters
from src.filters.filter_class import *  # Class-based filters
from src.filters.filter_id import *  # ID-based filters
from src.filters.filter_tag import *  # Tag-based filters
from src.extract_metadata import extract_metadata  # reuse existing metadata extractor (no reimplementation)
from dataclasses import dataclass
from playwright.sync_api import sync_playwright
from tkinter.scrolledtext import ScrolledText  # preview textbox with scroll
from tkinter import ttk  # ttk widgets for nicer UI
from pathlib import Path  # path utilities
from lxml import etree as ET
from typing import Iterable
import re, webbrowser, sys, json, tkinter as tk

_PROJECT_ROOT = ''
_TITLE = ''  # global document title for section removal dialog
_WHITESPACE = re.compile(r'\s+')  # regex to match whitespace sequences

@dataclass(frozen=True)
class Node:
    node : ET.Element  # reference to the element
    text : str  # extracted text
    lvl : int = 0  # heading level, 0 if not a heading

def html_to_text(doc_title: str, html: str, project_root) -> str:
    '''main function: HMTL -> Plaintext'''
    global _TITLE; _TITLE = doc_title
    global _PROJECT_ROOT; _PROJECT_ROOT = project_root
    if not html: return ''
    root = _html_to_ET(html)  # create lxml tree
    _insert_section_markers(root)
    raw = '\n'.join(block.text for block in _get_blocks(root))  # extract text blocks and join
    clean_txt = _merge_lines(raw)
    return clean_txt


def _html_to_ET(html: str) -> ET.Element:
    '''creates a correct working lxml tree'''
    import html5lib
    doc = html5lib.parse(html, treebuilder='lxml', namespaceHTMLElements=False)  # parse HTML
    return doc.getroot()

def _get_blocks(node: ET.Element) -> Iterable[Node]:
    '''recursive into lxml tree and extracts text blocks'''
    if _should_skip_node(node): return
    tag = _get_tag(node)
    
    if tag == 'table': 
        table = _get_table(node)
        yield Node(node=node, text=table)
        return  # table already added
                
    if tag in BLOCK_TAG:  # block-level element
        if (t := _clear_text(node)): yield Node(node=node, text=t)  # extract cleaned text
        return

    if node.text and (t := _normalize_whitespace(node.text)):  # text before children
        yield Node(node=node, text=t)  # yield text block

    for child in node:  # iterate children
        yield from _get_blocks(child)  # recursive call
        if child.tail and (t := _normalize_whitespace(child.tail)):  # text after child
            yield Node(node=child, text=t)  # yield text block

def _get_tag(node: ET.Element) -> str:
    '''returns the tag of the node in lowercase'''
    if isinstance(node.tag, str): return node.tag.lower()
    else: return ''  # node has no valid tag

def _get_table(node: ET.Element) -> str:
    i = 0
    row_txt = ''
    thead = []
    table = ''
    for tble_elem in node.iter():
        if _get_tag(tble_elem) == 'thead':  # get table head
            thead = []
            for t in tble_elem.iter():
                if _get_tag(t) == 'th' and _clear_text(t): thead.append(t.text.strip())
            continue
        if not thead: continue

        if _get_tag(tble_elem) == 'tr':
            for t in tble_elem.iter():
                if _get_tag(t) == 'td':
                    if not _clear_text(t) or _clear_text(t) == '?': 
                        i += 1
                        continue
                    if i < len(thead): row_txt += thead[i] + ': '
                    row_txt += _clear_text(t)
                    row_txt += '; '
                    i += 1
            if not row_txt: continue
            row_txt = row_txt[:-2].strip()  # removes last '; '
            if not row_txt.endswith(('.', '!', '?', ':', ';', '"', '“', '‘')): row_txt += '.'
            table += row_txt + '\n'
            row_txt = ''
            i = 0
    return table.strip()

def _should_skip_node(node: ET.Element) -> bool:
    '''determines if a node should be skipped based on filters'''
    def _skip_by_tag(tag: str) -> bool: return tag in SKIP_TAG
    def _skip_by_class(attr: dict[str, str]) -> bool:
        '''checks if any of the classes match the skip criteria'''
        classes = attr.get('class')
        if isinstance(classes, str):
            for c in classes.strip().lower().split():
                if c in SKIP_CLASS: return True  # exact match
                if any(c.startswith(p) for p in SKIP_CLASS_PREFIX): return True  # prefix match
                if any(substr in c for substr in SKIP_CLASS_CONTAINS): return True  # substring match
        return False  # no match found
    def _skip_by_attr(attr: dict[str, str]) -> bool:
        '''checks all attributes for skip criteria'''
        for name, value in attr.items():
            if isinstance(name, str): 
                name = name.strip().lower()
                if name in SKIP_ATTR: return True  # exact match
                if any(name.startswith(p) for p in SKIP_ATTR_PREFIX): return True  # prefix match
                if any(substr in name for substr in SKIP_ATTR_NAME_CONTAINS): return True  # substring match of name
            if isinstance(value, str):
                value = value.strip().lower()
                if any(substr in value for substr in SKIP_ATTR_VALUE_CONTAINS): return True  # substring match of value
        hidden = attr.get('aria-hidden')  # special case: aria-hidden = true
        if isinstance(hidden, str) and hidden.strip().lower() == 'true': return True
        return False  # no match found
    def _skip_by_id(attr: dict[str, str]) -> bool:
        '''checks the ID attribute for skip criteria'''
        id_val = attr.get('id')
        if id_val and isinstance(id_val, str):
            id_val = id_val.strip().lower()
            if id_val in SKIP_ID: return True  # exact match
            if any(id_val.startswith(p) for p in SKIP_ID_PREFIX): return True  # prefix match
            if any(substr in id_val for substr in SKIP_ID_CONTAINS): return True  # substring match
        return False  # no match found
    
    if not (tag := _get_tag(node)): return  True  # no valid tag found
    attr = node.attrib  # dict of all atrribs
    return (_skip_by_tag(tag) or _skip_by_class(attr) or _skip_by_attr(attr) or _skip_by_id(attr))  # any skip criteria met

def _clear_text(node: ET.Element) -> str:
    '''cleans up the text'''
    def _has_linebreak_child(node: ET.Element) -> bool:
        '''checks if there is a linebreak that should be considered'''
        return any((not _should_skip_node(child)) and (_get_tag(child) in BREAK_TAGS) for child in node)  # any linebreak child
    def _extract_only_text(node: ET.Element) -> Iterable[str]:
        '''extracts only text'''
        if _should_skip_node(node): return  # skip node

        if node.text: yield node.text  # yield text before children
        for child in node:
            skip = _should_skip_node(child)  # check if child should be skipped
            if not skip: yield from _extract_only_text(child)  # recursive call
            if child.tail: yield child.tail  # yield tail text after child

    if not (tag := _get_tag(node)): return ''

    parts = list(_extract_only_text(node))  # extract all text parts
    multiline = _has_linebreak_child(node)  # check for linebreak children

    sep = '\n' if multiline else (' ' if tag == 'tr' else ' ')  # separator based on context
    
    return _normalize_whitespace(sep.join(parts), multiline)

def _normalize_whitespace(text: str, multiline: bool = False) -> str:
        '''reduces whitespace and considers multiline with linebreaks'''
        clean = lambda s: _WHITESPACE.sub(' ', s).strip()  # function to clean whitespace
        if not multiline: return clean(text)  # single line

        lines = (clean(line) for line in text.splitlines())  # clean each line
        return '\n'.join(line for line in lines if line)  # join non-empty lines


def _get_headings(root: ET.Element) -> list[Node]:
    '''iterates over whole tree and returns all headings'''
    def _iter_visible(node):
        '''yields all visible nodes in the tree'''
        if _should_skip_node(node): return
        yield node
        for child in node: yield from _iter_visible(child)
    headings: list[Node] = []
    for node in _iter_visible(root):  # iterate over all visible nodes
        lvl = _get_lvl(node)
        if lvl is None: continue  # not a heading
        txt = _clear_text(node)
        if not txt: continue  # empty heading
        headings.append(Node(node, txt, lvl))  # add heading
    sect_one_lvl = headings[0].lvl if len(headings) > 0 else 99  # level of first heading
    headings.insert(0, Node(root, 'Intro', sect_one_lvl))  # add very first heading
    return headings

def _get_lvl(node: ET.Element) -> int | None:
    '''determines if the node is a heading and returns its level'''
    tag = _get_tag(node).lower()
    if len(tag) == 2 and tag.startswith('h') and tag[-1].isdigit(): return int(tag[-1])  # h1-h6 tags

    role = node.attrib.get('role')
    if isinstance(role, str) and role.strip().lower() == 'heading':  # role="heading"
        aria_level = node.attrib.get('aria-level')
        if isinstance(aria_level, str) and aria_level.strip().isdigit():  # aria-level attribute
            return int(aria_level.strip())  # return level
    return None  # not a heading

def _get_removal_ranges(all_headings: list[Node], to_remove: list[Node]) -> list[tuple[ET.Element, ET.Element | None]]:
    '''determines ranges of headings to remove'''
    ranges: list[tuple[ET.Element, ET.Element | None]] = []  # list of (start, end) tuples
    converted_until = -1 

    for i, start in enumerate(all_headings):
        if i < converted_until: continue  # already processed
        if start not in to_remove: continue  # not marked for removal

        end = None  # default end is None (till end of document)
        for j in range(i+1, len(all_headings)):  # find next heading of same or higher level
            h = all_headings[j]
            if h.lvl <= start.lvl and h not in to_remove:  # found next heading to stop at
                end = all_headings[j].node  # set end node
                converted_until = j
                break
        ranges.append((start.node, end))  # add range to list

    return ranges

def _remove_between(start: ET.Element, end: ET.Element | None) -> None:
    '''removes all nodes between start and end (exclusive)'''
    root = start.getroottree().getroot()  # get root of the tree
    nodes = list(root.iter())  # list of all nodes in document order

    if start not in nodes or (end is not None and end not in nodes): return  # nodes not found

    start_idx = nodes.index(start)  # find start index
    end_idx = nodes.index(end) if end is not None else len(nodes)  # find end index (or end of document)
    if end is not None and end_idx <= start_idx: return  # invalid range

    protected = set(end.iterancestors()) | {end} if end is not None else set()  # protect end and its ancestors

    for n in reversed(nodes[start_idx:end_idx]):  # iterate in reverse order
        if n in protected: continue  # skip protected nodes
        p = n.getparent()
        if p is not None: p.remove(n)  # remove node from parent


def _merge_lines(text: str) -> str:
    '''merges lines based on simple rules'''
    _OPEN = ('(', '[', '{')  # opening brackets
    _CLOSE = (')', ']', '}')  # closing brackets
    _SYMBOLS_ONLY = re.compile(r'^[\W_]+$')
    out = []
    in_br = False
    br = ''
    add_nxt = False
    for ln in text.splitlines():  # process line by line
        if not ln: continue  # skip empty lines
        if in_br:  # inside brackets
            br += ln  # append line to bracket content
            if ln.endswith(_CLOSE): 
                out.append(br)
                in_br = False
                br = ''  # reset bracket content
            continue
        if ln.endswith(_OPEN):  # line ends with opening bracket
            prev = out.pop() if out else ''  # get previous line
            br = (prev + ' ' if prev else '') + ln  # start new bracket content
            in_br = True
            continue            
        if add_nxt:  # append to previous line
            out[-1] += ' ' + ln
            add_nxt = False
            continue
        if _SYMBOLS_ONLY.match(ln) and out:  # line with only symbols
            out[-1] += ln
            add_nxt = True
        else: out.append(ln)  # normal line
        if ln.endswith(':'): add_nxt = True
        
    if in_br: out.append(br)
    merged = '\n'.join(out)  # join lines
    merged = re.sub(r'\s+(?=[)\]},;.:])', '', merged)  # remove space before closing punctuation
    merged = re.sub(r'([([{])\s+', r'\1', merged)  # remove space after opening punctuation
    return merged


def _insert_section_markers(root: ET.Element) -> None:
    '''inserts section markers into the tree'''
    headings = _get_headings(root)
    for h in headings:
        h.node.text = f'<<<SECTION: {h.text}; level: {h.lvl}>>>'  # insert marker


@dataclass  # simple container for one processed website (what the pipeline will write + chunk)
class Doc:  # returned objects from the GUI flow into process_html_files.py
    url: str  # the page URL (identity / debug / printing)
    title: str  # title used as directory + file prefix by your pipeline
    html: str  # raw HTML content (written as *_input.txt by the pipeline)
    text: str  # final plaintext (written as *_output.txt and chunked)
    metadata: dict[str, any]  # your metadata dict as produced by extract_metadata()
    state: dict[str, bool]  # per-section checkbox state saved to section_state.json

def download_html(url: str, ROOT: str):  # download a page without writing anything to disk (Abort must not write)
    _WIN_RESERVED = {  # these stuff cant be in name for dictionary or file on windows
        "CON","PRN","AUX","NUL",
        *(f"COM{i}" for i in range(1,10)),
        *(f"LPT{i}" for i in range(1,10)),
    }
    def safe_windows_name(name: str, fallback: str = "untitled") -> str:
        name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name)  # remove forbidden chars
        name = name.strip().strip(" .")  # remove dot at end
        name = re.sub(r"\s+", " ", name)  # remove whitespace
        if name.upper() in _WIN_RESERVED: name = "_" + name  # avoid reserved names
        name = name[:80].rstrip(" .")  # shorten if too long
        return name or fallback
    
    html, title = _load_cached_raw(url, ROOT)
    if html: return html, title
    
    global _PROJECT_ROOT; _PROJECT_ROOT = ROOT  # store project root for this module (paths/state)
    with sync_playwright() as p:  # open playwright session
        browser = p.chromium.launch(channel="msedge", headless=True)  # start headless browser (same as before)
        page = browser.new_page()  # create a new page/tab
        page.goto(url, wait_until="networkidle")  # load URL and wait until network is idle
        title = safe_windows_name(page.title())  # use document title
        html = page.content()  # get full HTML
        browser.close()  # close browser to free resources
    return html, title  # return in-memory only (no disk write here)

def _load_cached_raw(url: str, ROOT: str) -> tuple[str, str]:
    state_path = Path(ROOT) / "config/section_state.json"
    if not state_path.exists(): return "", ""
    data = json.loads(state_path.read_text(encoding="utf-8") or "{}")
    entry = data.get(url, {})
    if not isinstance(entry, dict): return "", ""
    title = entry.get("title", "")
    if title:
        raw_path = Path(ROOT) / "data" / title / f"{title}_raw.html"
        if raw_path.exists(): return (raw_path.read_text(encoding="utf-8"), title)
        else: return '', ''
    return '', ''

def _render_with_state(html: str, state: dict[str, bool]) -> str:  # render plaintext while removing unchecked sections
    root = _html_to_ET(html)  # parse HTML to lxml tree (fresh tree each time so we can safely modify)
    heads = _get_headings(root)  # compute headings list (includes your "Intro" injection)
    keys = [f"{i+1}. {h.text.strip()} (lvl: {h.lvl})" for i, h in enumerate(heads)]  # stable checkbox labels/keys
    to_remove = [heads[i] for i, k in enumerate(keys) if not state.get(k, True)]  # collect headings that are unchecked => remove
    ranges = _get_removal_ranges(heads, to_remove)  # convert headings to (start,end) removal ranges
    for start, end in reversed(ranges): _remove_between(start, end)  # remove ranges back-to-front to keep indices stable
    _insert_section_markers(root)  # insert SECTION markers AFTER removal so chunking sees only kept sections
    if keys and not state.get(keys[0], True): root.text = ''  # Intro unchecked => remove marker stored on root element
    raw = '\n'.join(block.text for block in _get_blocks(root))  # extract blocks from modified tree
    return _merge_lines(raw)  # merge/clean lines like in your normal pipeline


def process_multiple_docs(base_url: str, base_html: str, title: str, extracted_urls: list[tuple[str, int]], base_metadata, ROOT: str, SILENT: bool) -> list[Doc]:  # GUI that selects websites + sections and returns Docs
    if SILENT: return [Doc(base_url, title, base_html, html_to_text(title, base_html, ROOT), base_metadata, state=None)]
    win = tk.Tk()  # Root-Fenster sofort erstellen, damit tk.*Var später erlaubt ist
    win.title(f"Websites & Sections - {title}")  # Titel setzen
    win.geometry("1400x800")  # Startgröße setzen
    win.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))  # X soll das gesamte Programm beenden

    state_path = Path(ROOT) / "config/section_state.json"  # where section checkbox states are stored

    def load_state(key: str, keys: list[str]) -> dict[str, bool]:  # load per-document heading state (default all True)
        state = {k: True for k in keys}  # default: everything enabled
        if not state_path.exists(): return state  # no file yet => default
        try: data = json.loads(state_path.read_text(encoding="utf-8") or "{}")  # load JSON dict from disk
        except: return state  # invalid JSON => behave like empty
        doc = data.get(key, {}) if isinstance(data, dict) else {}  # per-document sub-dict
        sects = doc.get('sections', doc) if isinstance(doc, dict) else {}
        if isinstance(sects, dict): state.update({k: bool(sects.get(k, True)) for k in keys})  # merge stored values for existing keys
        return state  # return resolved state for this doc

    def save_state(url: str, site_title: str, state: dict[str, bool]) -> None:  # persist one document's state into section_state.json
        try: data = json.loads(state_path.read_text(encoding="utf-8") or "{}") if state_path.exists() else {}  # load file if present
        except: data = {}  # invalid file => overwrite with fresh dict
        if not isinstance(data, dict): data = {}  # enforce dict root
        data[url] = {"title": site_title, "sections": state}  # write/replace the document's state
        state_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")  # write back pretty JSON

    def state_key(meta: dict, url: str) -> str:  # stable key for state: prefer canonical_url, then url
        md = meta.get("metadata", {}) if isinstance(meta, dict) else {}  # metadata sub-dict
        return (md.get("canonical_url") or md.get("url") or url)  # canonical best, url fallback

    def init_site(url: str, html: str, title: str, meta: dict) -> None:  # initialize one site entry after download
        root = _html_to_ET(html)  # parse HTML so we can compute headings for the checkbox list
        heads = _get_headings(root)  # compute headings list for this HTML
        keys = [f"{i+1}. {h.text.strip()} (lvl: {h.lvl})" for i, h in enumerate(heads)]  # make the same keys used in the old dialog
        key = state_key(meta, url)  # compute stable JSON key for this page
        init = load_state(url, keys)  # load old state or default to all True
        vars_ = {k: tk.IntVar(master=win, value=(1 if init[k] else 0)) for k in keys}  # 1=checked, 0=unchecked (kein mixed state)
        sites[url] = {"dl": True, "save": True, "html": html, "title": title, "meta": meta, "key": key, "vars": vars_, "keys": keys}  # store everything for this site

    urls = list(dict.fromkeys([base_url] + [u for u, _ in extracted_urls]))  # unique URL list: base first, then extracted (keep order)
    sites = {u: {"dl": False, "save": False, "html": "", "title": "", "meta": None, "key": u, "vars": {}, "keys": []} for u in urls}  # in-memory cache per URL
    init_site(base_url, base_html, title, base_metadata)  # base site is already downloaded by pipeline => init now (loads old state)

    main = ttk.PanedWindow(win, orient="horizontal")  # 3-column layout: websites | sections | preview
    main.pack(fill="both", expand=True)  # make it fill the window

    left = tk.Frame(main); mid = tk.Frame(main, bg="#d5cece"); right = ttk.Frame(main)  # three panes
    main.add(left, weight=1); main.add(mid, weight=1); main.add(right, weight=2)  # preview gets more space
    
    left_top = ttk.Frame(left)              # oben: buttons
    left_top.pack(fill="x")                 # nimmt nur die Höhe die nötig ist

    left_body = ttk.Frame(left)             # unten: website-liste
    left_body.pack(fill="both", expand=True)# nimmt den restlichen Platz

    lb = tk.Listbox(left_body)  # website list widget
    sb = ttk.Scrollbar(left_body, orient="vertical", command=lb.yview)  # scrollbar for website list
    lb.configure(yscrollcommand=sb.set)  # connect list to scrollbar
    lb.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")  # pack list + scrollbar
    counts = dict(extracted_urls)  # url->count mapping for display (extracted list is already sorted by frequency)
    for u in urls: lb.insert("end", (f"BASE  {u}" if u == base_url else f"{counts.get(u, 0):>4}  {u}"))  # insert rows (base marked)
    row_of = {u: i for i, u in enumerate(urls)}  # map url -> listbox row index

    selected = tk.StringVar(master=win, value=base_url)  # aktuell ausgewählte URL an dieses Root binden
    save_var = tk.BooleanVar(master=win, value=True)  # Save-Checkbox an dieses Root binden

    open_btn = ttk.Button(left_top, text="open in browser")
    dl_btn = ttk.Button(left_top, text="download selected website")  # download button for current selection
    save_cb = ttk.Checkbutton(left_top, text="save selected website", variable=save_var)  # checkbox for current site saving
    open_btn.pack(fill="x"); dl_btn.pack(fill="x"); save_cb.pack(fill="x")

    sect_btns = ttk.Frame(mid)  # kleine Button-Leiste über den Sections
    sect_btns.pack(fill="x")    # oben in der Mitte platzieren

    canv = tk.Canvas(mid)  # scrollable container for section checkboxes
    msb = ttk.Scrollbar(mid, orient="vertical", command=canv.yview)  # vertical scroll for section list
    canv.configure(yscrollcommand=msb.set)  # connect canvas to scrollbar
    msb.pack(side="right", fill="y"); canv.pack(side="left", fill="both", expand=True)  # pack canvas + scrollbar
    sect_frame = ttk.Frame(canv)  # actual frame holding checkbuttons
    sect_win = canv.create_window((0, 0), window=sect_frame, anchor="nw")  # embed frame into canvas
    sect_frame.bind("<Configure>", lambda e: canv.configure(scrollregion=canv.bbox("all")))  # update scroll region when content changes
    canv.bind("<Configure>", lambda e: canv.itemconfigure(sect_win, width=e.width))  # keep checkbox width fitting the pane

    preview = ScrolledText(right, wrap="word")  # preview text area (right pane)
    preview.pack(fill="both", expand=True)  # fill right pane
    preview.configure(state="disabled")  # read-only: we only show rendered output

    btns = ttk.Frame(win)  # bottom bar with OK
    btns.pack(fill="x")  # stretch horizontally
    ok_btn = ttk.Button(btns, text="OK")  # OK saves state + returns docs
    ok_btn.pack(side="right", padx=10, pady=5)  # put button bottom-right

    result_docs: list[Doc] = []  # list of docs that will be returned to the pipeline

    def mark_all(on: int) -> None:  # on=1 => alles, on=0 => nichts
        url = current_url()  # aktuelle Website
        for v in sites[url]["vars"].values(): v.set(on)  # alle Sections setzen
        render_preview()  # Preview neu rendern (falls set() kein command auslöst)

    ttk.Button(sect_btns, text="Alles markieren", command=lambda: mark_all(1)).pack(side="left", fill="x", expand=True)
    ttk.Button(sect_btns, text="Nichts markieren", command=lambda: mark_all(0)).pack(side="left", fill="x", expand=True)


    def recolor_sites() -> None:  # color rows by export status
        for u in urls:  # go through all sites
            i = row_of[u]  # row index for this url
            bg = "white" if not sites[u]["dl"] else ("green" if sites[u]["save"] else "red")
            lb.itemconfigure(i, background=bg)  # apply background color to that row

    def current_url() -> str: return selected.get()  # helper to read the selected URL

    def current_state(url: str) -> dict[str, bool]:  # state dict for JSON + rendering
        return {k: bool(v.get()) for k, v in sites[url]["vars"].items()}  # IntVar -> bool

    def set_preview(txt: str) -> None:  # write text into preview widget (read-only update)
        preview.configure(state="normal"); preview.delete("1.0", "end"); preview.insert("1.0", txt); preview.configure(state="disabled")  # atomic replace

    def render_preview(*_) -> None:  # recompute preview text for current URL whenever something changes
        url = current_url()  # which URL is active in the UI
        if not sites[url]["dl"]: return set_preview("")  # not downloaded => empty preview
        return set_preview(_render_with_state(sites[url]["html"], current_state(url)))  # render text after removing unchecked sections

    def rebuild_sections() -> None:  # rebuild the middle pane (section checkbox list) for the current URL
        for w in sect_frame.winfo_children(): w.destroy()  # clear old checkboxes
        url = current_url()  # active URL
        if not sites[url]["dl"]: return render_preview()  # nothing to show if not downloaded
        for k in sites[url]["keys"]:
            v = sites[url]["vars"][k]
            ttk.Checkbutton(sect_frame, text=k, variable=v, command=render_preview).pack(anchor="w")  # click => rerender
        render_preview()

    def on_select(_=None) -> None:  # handler when user selects another website in the left list
        sel = lb.curselection()  # current selection indices
        if not sel: return  # no selection => nothing to do
        url = urls[sel[0]]  # map listbox index back to URL (same order as insertion)
        selected.set(url)  # update selected URL variable
        if not sites[url]["dl"]:  # not loaded in RAM yet
            html, title = _load_cached_raw(url, ROOT)  # try disk cache ONLY (no download)
            if html: init_site(url, html, title, extract_metadata(html))  # if cached => load + build section vars
            save_var.set(False)  # optional: beim Nicht-Download Häkchen rausnehmen
        save_cb.configure(state=("normal" if sites[url]["dl"] else "disabled"))  # grau wenn nicht downloaded

        save_var.set(bool(sites[url]["save"]))  # show current "save" state of this URL
        rebuild_sections()  # refresh sections+preview for the newly selected URL

    def on_save_toggle(*_) -> None:  # handler for toggling "save selected website"
        sites[current_url()]["save"] = save_var.get()  # write checkbox state into our per-site cache
        recolor_sites()

    def on_download() -> None:  # download button handler for current selection
        url = current_url()  # current website URL
        if sites[url]["dl"]: return  # already downloaded => do nothing
        html, title = download_html(url, ROOT)  # download (no disk write)
        init_site(url, html, title, extract_metadata(html))  # compute headings, load old state, mark save=True
        save_var.set(True)  # requirement: downloading auto-enables saving for this website
        save_cb.configure(state="normal")  # nach Download wieder aktiv
        recolor_sites()
        rebuild_sections()  # show sections and preview now that the page exists

    def on_open() -> None:
        sel = lb.curselection()
        if sel: webbrowser.open_new_tab(urls[sel[0]])

    def on_ok() -> None:  # OK button: for all marked websites -> save state + return docs
        for url, info in sites.items():  # iterate through all known URLs
            if not info["save"]: continue  # only process websites that are marked for saving
            if not info["dl"]:  # if user marked a site but never downloaded it manually
                html, title = download_html(url, ROOT)  # download it now so we can process it
                init_site(url, html, title, extract_metadata(html))  # initialize cache (state loaded, save forced true)
                info = sites[url]  # refresh local reference after init_site overwrote the dict
            state = current_state(url)  # grab final section checkbox state from UI vars
            save_state(url, info['title'], state)  # requirement: store state on OK per marked website
            txt = _render_with_state(info["html"], state)  # render final text for this website with selected sections
            result_docs.append(Doc(url=url, title=info["title"], html=info["html"], text=txt, metadata=info["meta"], state=state))  # create output object for pipeline
        win.destroy()  # close window and return to pipeline (next getURLs.txt window opens)

    lb.bind("<<ListboxSelect>>", on_select)  # connect website selection event
    save_var.trace_add("write", on_save_toggle)  # connect save checkbox toggles
    dl_btn.configure(command=on_download)  # connect download button
    open_btn.configure(command=on_open)
    ok_btn.configure(command=on_ok)  # connect OK button

    lb.selection_set(0)  # select first row (base URL) by default
    on_select()  # build initial sections+preview for base URL right away
    win.mainloop()  # block until window is closed (OK/Abort/X)

    return result_docs  # Abort => nothing; OK => docs for pipeline
