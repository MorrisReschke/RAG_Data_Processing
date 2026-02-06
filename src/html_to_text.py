from src.config.filters.filter_attribute import *  # Attribute-based filters
from src.config.filters.filter_class import *  # Class-based filters
from src.config.filters.filter_id import *  # ID-based filters
from src.config.filters.filter_tag import *  # Tag-based filters
from dataclasses import dataclass
from lxml import etree as ET
from typing import Iterable
import re

_PROJECT_ROOT = ''
_TITLE = ''  # global document title for section removal dialog
_WHITESPACE = re.compile(r'\s+')  # regex to match whitespace sequences
_HEADINGS = []

@dataclass(frozen=True)
class Node:
    node : ET.Element  # reference to the element
    text : str  # extracted text
    lvl : int = 0  # heading level, 0 if not a heading

def html_to_text(doc_title: str, html: str, project_root, urls: list[str]) -> str:
    '''main function: HMTL -> Plaintext'''
    global _TITLE; _TITLE = doc_title
    global _PROJECT_ROOT; _PROJECT_ROOT = project_root
    if not html: return ''
    root = _html_to_ET(html)  # create lxml tree
    _remove_custom_sections(root)
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


def _remove_custom_sections(root: ET.Element) -> None:
    '''removes user-selected sections based on headings'''
    global _HEADINGS
    _HEADINGS = _get_headings(root)
    if not _HEADINGS: return  # no headings found
    
    to_remove = _get_headings_to_remove(root, _HEADINGS)
    if not to_remove: return  # nothing to remove
    
    ranges = _get_removal_ranges(_HEADINGS, to_remove)  # get removal ranges
    for start, end in reversed(ranges): _remove_between(start, end)  # remove in reverse order

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

def _get_headings_to_remove(root: ET.Element, headings: list[Node]) -> list[Node]:
    '''displays a dialog to select headings to remove'''
    import copy, json, tkinter as tk
    from tkinter import ttk
    from tkinter.scrolledtext import ScrolledText

    path = f'{_PROJECT_ROOT}/src/config/section_state.json'  # path to state file
    keys = [f'{i+1}. {h.text.strip()} (lvl: {h.lvl})' for i, h in enumerate(headings)]  # keys for state

    def load_state() -> dict[str, bool]:
        '''loads the saved state from file'''
        state = {k: True for k in keys}  # default: all selected
        try:
            with open(path, "r", encoding="utf-8") as f: data = json.load(f)  # load JSON
        except (FileNotFoundError, json.JSONDecodeError): return state
        doc = data.get(_TITLE, {}) if isinstance(data, dict) else {}  # get doc-specific data
        if isinstance(doc, dict): state.update({k: bool(doc.get(k, True)) for k in keys})  # update state
        return state
    def save_state(state_vars: dict[str, tk.BooleanVar]) -> None:
        '''saves the current state to file'''
        doc_data = {k: v.get() for k, v in state_vars.items()}  # extract current state
        try:
            with open(path, "r", encoding="utf-8") as f: data = json.load(f)  # load existing data
        except (FileNotFoundError, json.JSONDecodeError): data = {}
        if not isinstance(data, dict): data = {}
        data[_TITLE] = doc_data
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)  # save JSON
    def render_preview() -> None:
        '''renders the preview based on current selection'''
        nonlocal state
        tmp_root = copy.deepcopy(root)  # temporary copy of the tree
        tmp_heads = _get_headings(tmp_root)  # temporary headings

        to_remove_idx = [i for i, k in enumerate(keys) if not state[k].get()]  # indices to remove
        tmp_remove = [tmp_heads[i] for i in to_remove_idx if i < len(tmp_heads)]  # corresponding nodes

        if tmp_remove:
            tmp_ranges = _get_removal_ranges(tmp_heads, tmp_remove)  # get removal ranges
            for start, end in reversed(tmp_ranges): _remove_between(start, end)  # remove in reverse order

        raw = "\n".join(block.text for block in _get_blocks(tmp_root))  # extract text blocks
        txt = _merge_lines(raw)  # merge lines

        preview.configure(state="normal")
        preview.delete("1.0", "end")
        preview.insert("1.0", txt)
        preview.configure(state="disabled")
    def ok() -> None:
        '''handles OK button press'''
        nonlocal result
        result = [headings[i] for i, k in enumerate(keys) if not state[k].get()]  # extract selected headings
        save_state(state)  # save current state
        select_win.destroy()
    def abort() -> None:
        '''handles window close'''
        import sys
        sys.exit(0)
    
    select_win = tk.Tk()  # create main window
    # region GUI
    select_win.title("Select Headings to Remove")
    select_win.geometry("1100x800")
    tk.Label(select_win, text="Uncheck headings you want to REMOVE.").pack(pady=8)

    paned = ttk.PanedWindow(select_win, orient="horizontal")  # create paned window
    paned.pack(fill="both", expand=True, padx=10, pady=(0, 10))  # pack paned window
    left = ttk.Frame(paned)  # left frame for checkboxes
    right = ttk.Frame(paned)  # right frame for preview
    paned.add(left, weight=1)  # add frames to paned window
    paned.add(right, weight=3)  # right frame larger

    # --- left window ---
    c = tk.Canvas(left)
    sb = ttk.Scrollbar(left, orient="vertical", command=c.yview)
    c.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")  # scrollbar on right
    c.pack(side="left", fill="both", expand=True)  # canvas on left

    f = ttk.Frame(c)
    w = c.create_window((0, 0), window=f, anchor="nw")
    f.bind("<Configure>", lambda e: c.configure(scrollregion=c.bbox("all")))  # update scrollregion
    c.bind("<Configure>", lambda e: c.itemconfigure(w, width=e.width))  # update frame width
    
    # --- right window ---
    preview = ScrolledText(right, wrap="word")
    preview.pack(fill="both", expand=True)
    preview.configure(state="disabled")
    # endregion
    
    init = load_state()
    state = {k: tk.BooleanVar(value=init[k]) for k in keys}  # create state variables

    for k, v in state.items():  # create checkboxes
        ttk.Checkbutton(f, text=k, variable=v).pack(anchor="w")
        v.trace_add("write", lambda *_: render_preview())  # update preview on change

    result: list[Node] = []
    ttk.Button(select_win, text="OK", command=ok).pack(pady=(0, 10))  # OK button
    select_win.protocol("WM_DELETE_WINDOW", abort)  # handle window close

    render_preview()  # initial preview render
    select_win.mainloop()
    return result

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

# =========================  MINIMAL MULTI-SITE SESSION  =========================  # NEW

class DocumentState:  # NEW
    def __init__(  # NEW
        self,  # NEW
        url_requested: str,  # NEW
        base_name: str,  # NEW
        html: str,  # NEW
        metadata: dict[str, any],  # NEW
        canonical_url: str | None,  # NEW
        urls_ranked: list[tuple[str, int]],  # NEW
        root: ET.Element,  # NEW
    ):  # NEW
        self.url_requested = url_requested  # NEW
        self.base_name = base_name  # NEW
        self.html = html  # NEW
        self.metadata = metadata  # NEW
        self.canonical_url = canonical_url  # NEW
        self.urls_ranked = urls_ranked  # NEW
        self.root = root  # NEW
        self.heading_keys: list[str] = []  # NEW
        self.heading_state: dict[str, bool] = {}  # NEW
        self.next_url_idx: int = 0  # NEW
        self.final_text: str = ''  # NEW

def review_session(initial_docs: list[DocumentState], load_doc_fn):  # NEW
    import copy  # NEW
    import tkinter as tk  # NEW
    from tkinter import ttk, messagebox  # NEW
    from tkinter.scrolledtext import ScrolledText  # NEW

    import json  # NEW
    from pathlib import Path  # NEW

    path = Path(__file__).resolve().parent / "config" / "section_state.json"  # NEW

    def load_state(doc_key: str, keys: list[str]) -> dict[str, bool]:  # NEW
        state = {k: True for k in keys}  # NEW
        try:  # NEW
            with open(path, "r", encoding="utf-8") as f:  # NEW
                data = json.load(f)  # NEW
        except (FileNotFoundError, json.JSONDecodeError):  # NEW
            return state  # NEW
        doc = data.get(doc_key, {}) if isinstance(data, dict) else {}  # NEW
        if isinstance(doc, dict):  # NEW
            state.update({k: bool(doc.get(k, True)) for k in keys})  # NEW
        return state  # NEW

    def save_all_states() -> None:  # NEW
        try:  # NEW
            with open(path, "r", encoding="utf-8") as f:  # NEW
                data = json.load(f)  # NEW
        except (FileNotFoundError, json.JSONDecodeError):  # NEW
            data = {}  # NEW
        if not isinstance(data, dict):  # NEW
            data = {}  # NEW

        for d in docs:  # NEW
            if not d.heading_keys:  # NEW
                continue  # NEW
            data[d.base_name] = {k: bool(d.heading_state.get(k, True)) for k in d.heading_keys}  # NEW

        path.parent.mkdir(parents=True, exist_ok=True)  # NEW
        with open(path, "w", encoding="utf-8") as f:  # NEW
            json.dump(data, f, ensure_ascii=False, indent=2)  # NEW
    
    docs: list[DocumentState] = list(initial_docs or [])  # NEW
    if not docs:  # NEW
        return []  # NEW

    loaded: set[str] = set()  # NEW
    seed_doc = docs[0]  # NEW
    seed_next = {"i": 0}  # NEW
    for d in docs:  # NEW
        if d.url_requested: loaded.add(d.url_requested)  # NEW
        if d.canonical_url: loaded.add(d.canonical_url)  # NEW

    def ensure_keys(doc: DocumentState) -> None:  # NEW
        if doc.heading_keys:  # NEW
            return  # NEW
        heads = _get_headings(doc.root)  # NEW
        doc.heading_keys = [f'{i+1}. {h.text.strip()} (lvl: {h.lvl})' for i, h in enumerate(heads)]  # NEW
        doc.heading_state = load_state(doc.base_name, doc.heading_keys)  # CHANGED


    def preview_text(doc: DocumentState) -> str:  # NEW
        ensure_keys(doc)  # NEW
        tmp_root = copy.deepcopy(doc.root)  # NEW
        tmp_heads = _get_headings(tmp_root)  # NEW
        to_remove_idx = [i for i, k in enumerate(doc.heading_keys) if not doc.heading_state.get(k, True)]  # NEW
        tmp_remove = [tmp_heads[i] for i in to_remove_idx if i < len(tmp_heads)]  # NEW
        if tmp_remove:  # NEW
            tmp_ranges = _get_removal_ranges(tmp_heads, tmp_remove)  # NEW
            for start, end in reversed(tmp_ranges):  # NEW
                _remove_between(start, end)  # NEW
        raw = "\n".join(block.text for block in _get_blocks(tmp_root))  # NEW
        return _merge_lines(raw)  # NEW

    def apply_removals_inplace(doc: DocumentState) -> None:  # NEW
        ensure_keys(doc)  # NEW
        heads = _get_headings(doc.root)  # NEW
        to_remove_idx = [i for i, k in enumerate(doc.heading_keys) if not doc.heading_state.get(k, True)]  # NEW
        to_remove = [heads[i] for i in to_remove_idx if i < len(heads)]  # NEW
        if to_remove:  # NEW
            ranges = _get_removal_ranges(heads, to_remove)  # NEW
            for start, end in reversed(ranges):  # NEW
                _remove_between(start, end)  # NEW

    def finalize_text(doc: DocumentState) -> str:  # NEW
        _insert_section_markers(doc.root)  # NEW
        raw = "\n".join(block.text for block in _get_blocks(doc.root))  # NEW
        return _merge_lines(raw)  # NEW

    win = tk.Tk()  # NEW
    win.title("Section Review (Multi-Site)")  # NEW
    win.geometry("1200x850")  # NEW

    top = ttk.Frame(win)  # NEW
    top.pack(fill="x", padx=10, pady=8)  # NEW

    title_lbl = ttk.Label(top, text="")  # NEW
    title_lbl.pack(side="left")  # NEW

    nav = ttk.Frame(top)  # NEW
    nav.pack(side="right")  # NEW
    prev_btn = ttk.Button(nav, text="Prev")  # NEW
    prev_btn.pack(side="left", padx=(0, 6))  # NEW
    next_btn = ttk.Button(nav, text="Next")  # NEW
    next_btn.pack(side="left")  # NEW

    paned = ttk.PanedWindow(win, orient="horizontal")  # NEW
    paned.pack(fill="both", expand=True, padx=10, pady=(0, 10))  # NEW
    left = ttk.Frame(paned)  # NEW
    right = ttk.Frame(paned)  # NEW
    paned.add(left, weight=1)  # NEW
    paned.add(right, weight=3)  # NEW

    c = tk.Canvas(left)  # NEW
    sb = ttk.Scrollbar(left, orient="vertical", command=c.yview)  # NEW
    c.configure(yscrollcommand=sb.set)  # NEW
    sb.pack(side="right", fill="y")  # NEW
    c.pack(side="left", fill="both", expand=True)  # NEW
    f = ttk.Frame(c)  # NEW
    w = c.create_window((0, 0), window=f, anchor="nw")  # NEW
    f.bind("<Configure>", lambda e: c.configure(scrollregion=c.bbox("all")))  # NEW
    c.bind("<Configure>", lambda e: c.itemconfigure(w, width=e.width))  # NEW

    preview = ScrolledText(right, wrap="word")  # NEW
    preview.pack(fill="both", expand=True)  # NEW
    preview.configure(state="disabled")  # NEW

    bottom = ttk.Frame(win)  # NEW
    bottom.pack(fill="x", padx=10, pady=(0, 10))  # NEW
    ttk.Label(bottom, text="Ranked URLs (count → url):").pack(anchor="w")  # NEW

    url_row = ttk.Frame(bottom)  # NEW
    url_row.pack(fill="x")  # NEW
    url_list = tk.Listbox(url_row, height=7)  # NEW
    url_list.pack(side="left", fill="both", expand=True)  # NEW
    url_sb = ttk.Scrollbar(url_row, orient="vertical", command=url_list.yview)  # NEW
    url_list.configure(yscrollcommand=url_sb.set)  # NEW
    url_sb.pack(side="left", fill="y")  # NEW

    load_next_btn = ttk.Button(url_row, text="Load next")  # NEW
    load_next_btn.pack(side="left", padx=10)  # NEW

    footer = ttk.Frame(win)  # NEW
    footer.pack(fill="x", padx=10, pady=10)  # NEW
    ok_btn = ttk.Button(footer, text="OK")  # NEW
    ok_btn.pack(side="right")  # NEW

    cur = {"i": 0}  # NEW

    def render_doc(i: int) -> None:  # NEW
        cur["i"] = max(0, min(i, len(docs) - 1))  # NEW
        doc = docs[cur["i"]]  # NEW
        ensure_keys(doc)  # NEW
        title_lbl.configure(text=f'{cur["i"]+1}/{len(docs)}  {doc.base_name}')  # NEW

        for child in list(f.winfo_children()):  # NEW
            child.destroy()  # NEW

        vars_by_key: dict[str, tk.BooleanVar] = {}  # NEW

        def on_toggle(k: str) -> None:  # NEW
            doc.heading_state[k] = vars_by_key[k].get()  # NEW
            txt = preview_text(doc)  # NEW
            preview.configure(state="normal")  # NEW
            preview.delete("1.0", "end")  # NEW
            preview.insert("1.0", txt)  # NEW
            preview.configure(state="disabled")  # NEW

        for k in doc.heading_keys:  # NEW
            v = tk.BooleanVar(value=doc.heading_state.get(k, True))  # NEW
            vars_by_key[k] = v  # NEW
            ttk.Checkbutton(f, text=k, variable=v, command=lambda kk=k: on_toggle(kk)).pack(anchor="w")  # NEW

        url_list.delete(0, "end")  # (unverändert)
        for u, cnt in seed_doc.urls_ranked:  # CHANGED
            mark = " [loaded]" if (u in loaded) else ""  # (unverändert)
            url_list.insert("end", f"{cnt:>4}  {u}{mark}")  # (unverändert)


        txt = preview_text(doc)  # NEW
        preview.configure(state="normal")  # NEW
        preview.delete("1.0", "end")  # NEW
        preview.insert("1.0", txt)  # NEW
        preview.configure(state="disabled")  # NEW

    def on_prev() -> None:  # NEW
        render_doc(cur["i"] - 1)  # NEW

    def on_next() -> None:  # NEW
        render_doc(cur["i"] + 1)  # NEW

    def on_load_next() -> None:
        i = seed_next["i"]  # CHANGED
        while i < len(seed_doc.urls_ranked) and seed_doc.urls_ranked[i][0] in loaded:  # CHANGED
            i += 1  # (unverändert)
        seed_next["i"] = i + 1  # CHANGED
        if i >= len(seed_doc.urls_ranked):  # CHANGED
            messagebox.showinfo("No more URLs", "No more unseen URLs in this list.")  # (unverändert)
            return  # (unverändert)

        url = seed_doc.urls_ranked[i][0]  # CHANGED
        try:  # (unverändert)
            new_doc = load_doc_fn(url)  # (unverändert)
        except Exception as e:  # (unverändert)
            messagebox.showerror("Load failed", str(e))  # (unverändert)
            return  # (unverändert)

        loaded.add(url)  # (unverändert)
        if new_doc.canonical_url: loaded.add(new_doc.canonical_url)  # (unverändert)
        docs.append(new_doc)  # (unverändert)
        render_doc(len(docs) - 1)  # (unverändert)


    def on_ok() -> None:  # NEW
        for d in docs:  # NEW
            apply_removals_inplace(d)  # NEW
            d.final_text = finalize_text(d)  # NEW
        save_all_states()  # NEW
        win.destroy()  # NEW

    prev_btn.configure(command=on_prev)  # NEW
    next_btn.configure(command=on_next)  # NEW
    load_next_btn.configure(command=on_load_next)  # NEW
    ok_btn.configure(command=on_ok)  # NEW

    def abort() -> None:  # NEW
        import sys  # NEW
        sys.exit(0)  # NEW

    win.protocol("WM_DELETE_WINDOW", abort)  # NEW
    render_doc(0)  # NEW
    win.mainloop()  # NEW
    return docs  # NEW
