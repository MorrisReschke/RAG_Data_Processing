from bs4 import BeautifulSoup

def main2(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser") 
    return soup.get_text(' ', strip=True)

def main(html: str) -> str:
    """
    Robust-ish Text-Extraktion mit (nahezu) nur bs4-Features:
    - Parse Tree bauen
    - Offensichtliche Nicht-Inhalts-Tags entfernen
    - Haupt-Container heuristisch auswählen (main/article/role=main oder bestes Text-vs-Link-Verhältnis)
    - Text blockweise (Überschriften/Absätze/Listen/…) extrahieren, ohne regex
    """
    from bs4 import Comment

    if not html or not html.strip():
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # 1) Kommentare entfernen
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()

    # 2) Offensichtlich nicht-inhaltliche Tags entfernen
    drop_tags = [
        "script", "style", "noscript", "template",
        "svg", "canvas", "iframe",
        "form", "input", "button", "select", "option", "textarea",
        "nav", "header", "footer", "aside",
    ]
    for t in soup.find_all(drop_tags):
        t.decompose()

    # 3) Grob "versteckte" Elemente entfernen (CSS-Selector ist Teil des bs4-Workflows)
    for t in soup.select(
        '[hidden], [aria-hidden="true"], '
        '[style*="display:none"], [style*="display: none"], '
        '[style*="visibility:hidden"], [style*="visibility: hidden"]'
    ):
        t.decompose()

    root = soup.body or soup

    # 4) Kandidaten finden (erst explizite Content-Hinweise, dann größere Container)
    candidates = []

    # bevorzugte "Main content" Knoten
    for tag_name in ("main", "article"):
        el = root.find(tag_name)
        if el:
            candidates.append(el)

    el = root.find(attrs={"role": "main"})
    if el:
        candidates.append(el)

    # häufige IDs/Klassen (nur bs4, keine externen Tools)
    for el in root.select("#content, #main, .content, .main, .post, .article, .entry-content, .post-content"):
        candidates.append(el)

    # größere Blöcke als Fallback
    candidates.extend(root.find_all(["article", "main", "section", "div"], limit=2000))

    def score(node) -> float:
        # Text gut, Link-lastig eher schlecht (Nav/Sidebar)
        text = node.get_text(" ", strip=True)
        if not text:
            return 0.0

        text_len = len(text)

        links = node.find_all("a", limit=1000)
        link_count = len(links)
        link_text_len = 0
        for a in links[:300]:  # cap, damit nicht zu teuer
            link_text_len += len(a.get_text(" ", strip=True))

        # einfache Heuristik
        return text_len - 0.7 * link_text_len - 5.0 * max(0, link_count - 20)

    best = max(candidates, key=score, default=root)

    # 5) Blockweise Extraktion (verhindert "alles in einer Zeile")
    block_tags = {
        "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "li", "blockquote", "pre",
        "dt", "dd", "figcaption", "caption",
        "tr", "th", "td",
    }

    blocks: list[str] = []

    def normalize_inline_ws(s: str) -> str:
        # ohne regex: alle Whitespace-Sequenzen -> 1 Space
        # (split() behandelt auch \n \t etc.)
        return " ".join(s.split())

    for t in best.find_all(list(block_tags)):
        # Doppelte Inhalte vermeiden: überspringe, wenn ein Block-Parent existiert
        parent_block = t.find_parent(list(block_tags))
        if parent_block is not None:
            continue

        if t.name == "pre":
            # Preformatted: Zeilenumbrüche behalten (bs4 kann Separator setzen)
            txt = t.get_text("\n", strip=True)
            if txt:
                blocks.append(txt)
            continue

        txt = normalize_inline_ws(t.get_text(" ", strip=True))
        if txt:
            blocks.append(txt)

    if not blocks:
        # Fallback: alles zusammenziehen (schnell & "dirty", aber oft okay)
        return normalize_inline_ws(best.get_text(" ", strip=True))

    # 6) Ausgabe: Absätze durch Leerzeile trennen (chunking-freundlich)
    return "\n\n".join(blocks).strip()
