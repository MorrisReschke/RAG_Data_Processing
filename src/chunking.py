import re, copy
from dataclasses import dataclass
MARKER_PREFIX = '<<<SECTION: '
MARKER_SUFFIX = '>>>'
MAX_CHUNK_LENGTH = 200
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-ZÄÖÜ0-9"„“‚‘(])')

@dataclass
class Section:
    heading : str = ''
    lvl : int = -1
    text : str = ''
    got_split : bool = False

def chunking(base_name: str, text: str, meta_default: dict[str, any]):
    '''chunks the text into sections based on markers and writes to JSONL'''
    def _get_content_hash(text: str) -> str:
        import hashlib
        norm = ' '.join(text.split())
        return hashlib.sha256(norm.encode('utf-8')).hexdigest()
    
    chunk_txt = ['']
    sects_in_chunk: list[list[Section]] = [[]]
    chunk_length = 0
    prev2 = prev1 = ''
    
    for sect in _get_sections(text):
        sect_length = _count_words(sect.text)
        if chunk_length + sect_length <= MAX_CHUNK_LENGTH:  # next section can be added completly
            chunk_txt[-1] += sect.text + ' '  # add whole section
            sects_in_chunk[-1].append(sect)
            chunk_length += sect_length  # new chunk length
            tail = _get_sentences(sect.text)
            if tail: prev2, prev1 = (tail[-2] if len(tail) > 1 else prev1), tail[-1]
        else:  # next section needs to be splitted
            sentences = _get_sentences(sect.text)
            added_to_current = False
            for s in sentences:  # iterate over all sentence
                sentence_length = _count_words(s)
                if chunk_length + sentence_length <= MAX_CHUNK_LENGTH:  # sentence can be added
                    if not added_to_current:
                        sects_in_chunk[-1].append(sect)
                        sect.got_split = True
                        added_to_current = True
                    chunk_txt[-1] += s + ' '  # add sentence to chunk
                    prev2, prev1 = prev1, s
                    chunk_length += sentence_length  # update chunk length
                else:  # sentence needs to go in next chunk
                    overlap = (prev2 + ' ' + prev1).strip()
                    chunk_txt.append(((overlap + ' ' + s).strip() + ' '))  # add overlap and sentence to new chunk
                    sects_in_chunk.append([sect])
                    if added_to_current: sect.got_split = True
                    added_to_current = True
                    chunk_length = _count_words(chunk_txt[-1])  # update chunk length
                    prev2, prev1 = prev1, s
    
    out = []
    char_pos = 0
    overlap = 0
    for i, txt in enumerate(chunk_txt):
        if not txt: continue
        content_hash = _get_content_hash(txt)
        nxt_line = copy.deepcopy(meta_default)  # new default line
        nxt_line['id'] = meta_default['id'] + str(i)
        nxt_line['text'] = txt.strip()
        nxt_line['metadata']['headings'] = [{'heading': s.heading, 'lvl': s.lvl, 'got_split': s.got_split} for s in sects_in_chunk[i]]
        nxt_line['metadata']['chunk_index'] = i
        nxt_line['metadata']['word_count'] = _count_words(txt)
        nxt_line['metadata']['start_char'] = char_pos
        char_pos += len(txt.strip())
        nxt_line['metadata']['end_char'] = char_pos
        nxt_line['metadata']['overlap_char'] = overlap
        if len(_get_sentences(txt)) < 2: raise Exception('Overlap is not possible. Probably because MAX_CHUNK_LENGTH is too low.')
        overlap = len(_get_sentences(txt)[-2] + ' ' + _get_sentences(txt)[-1])
        char_pos -= overlap
        nxt_line['metadata']['content_hash'] = content_hash
        out.append(nxt_line)
    return out

def _get_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text: return []
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]

def _get_sections(text: str):
    def make_output(heading: str, lvl: int, txt: str):
        length = _count_words(txt)
        if length < 5: return None  # kill very short lines
        return Section(heading, lvl, txt, False)    
    def parse_marker(line: str):
        '''parses a section marker line'''
        end_idx = line.find(MARKER_SUFFIX)
        inner = line[len(MARKER_PREFIX) : end_idx]  # extract inner content
        heading, lvl = inner.split('; level: ')
        return heading.strip(), int(lvl.strip())
    sect_txt = ''
    heading = None
    first = True
    for ln in text.splitlines():  # process each line
        ln = ln.strip()
        if ln.startswith(MARKER_PREFIX):  # found a section marker
            if not first:  # not the first marker
                out = make_output(heading, lvl, sect_txt.strip())
                if out: yield out
                sect_txt = ''
            first = False
            heading, lvl = parse_marker(ln)  # parse marker
            continue
        sect_txt += ln + ' '

    out = make_output(heading, lvl, sect_txt.strip())
    if out: yield out

def _count_words(text: str) -> int: return len(text.strip().split())

