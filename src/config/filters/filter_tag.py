# --- TAG-LEVEL FILTERS ----------------------------------------------------
# Tags whose content is almost never useful text for RAG
SKIP_TAG = {
    # Non-visible metadata & resources
    "script",      # JS code, e.g. <script>...</script>
    "style",       # CSS rules, e.g. <style>...</style>
    "noscript",    # JS fallbacks – usually duplicate/noisy
    "head",        # metadata container (<title>, <meta>, <link>, …)
    "meta",        # single metadata tags, e.g. <meta charset="utf-8">
    "link",        # external resources (CSS, icons, feeds)
    "template",    # inert templates for JS frameworks
    "math",        # MathML structures, rarely good as plain text
    "text",        # SVG <text> nodes, not HTML body text

    # Embedded media / plugins (visual, not textual)
    "iframe",      # embedded pages (YouTube, ads, widgets)
    "audio",       # audio player wrapper
    "video",       # video player wrapper
    "source",      # media source (<source src="...">)
    "track",       # subtitles / captions metadata
    "object",      # generic embedded object (Flash, etc.)
    "embed",       # plugin embed (legacy)
    "canvas",      # script-drawn graphics, no real text
    "svg",         # vector graphics container
    "picture",     # responsive image wrapper
    "map",         # image map container
    "area",        # clickable region in <map>

    # Forms & controls (UI, mostly boilerplate)
    "form",        # whole form block (login, search, newsletter)
    "input",       # input fields, e.g. <input type="text">
    "textarea",    # large input area, user-generated not page text
    "button",      # UI buttons, e.g. "Submit", "Search"
    "select",      # dropdowns (country lists, etc.)
    "option",      # single option in <select>
    "label",       # form labels, usually microcopy
    "figcaption",  # caption below/above a figure

    # Layout / chrome containers that are rarely article content
    "nav",         # site or app navigation container
    "footer",      # page footer (legal, copyright, backlinks)
    "menu",        # HTML5 menu, rarely used for article text
    "aside",       # complementary content (side notes, sidebars)

    # old
    "frame",
    "frameset",

    # often too aggressive
    "header",
}

# Tags that usually represent a self-contained textual block
BLOCK_TAG = {
    # Core block-level text units
    "p",                  # paragraph, <p>...</p>
    "li",                 # list item, <li>Item</li>
    "h1", "h2", "h3",
    "h4", "h5", "h6",     # headings, <h2>History</h2>
    "blockquote",         # quoted section, <blockquote>…</blockquote>

    # Preformatted / code
    "pre",                # preformatted text (ASCII tables, code)
    "code",               # code snippets, inline or block-style

    # Tabular & structured text
    "tr",                 # table row; you already aggregate cells
    "caption",            # <caption> for tables
    "dt",                 # term in definition list
    "dd",                 # description in definition list

    # Misc textual containers
    "address",            # contact/author info
    "summary",            # visible header of <details> block
}

# Child tags that imply meaningful line breaks inside a block
BREAK_TAGS = {
    # Hard line breaks
    "br",                 # explicit line break, <br>

    # List-like structures inside a block
    "ul",                 # unordered list, children are <li>
    "ol",                 # ordered list, children are <li>
    "li",                 # separate list items as individual lines

    # Definition lists inside blocks
    "dt",                 # term, rendered on its own line
    "dd",                 # description, often line below the term

    # Nested paragraphs inside a block (e.g. within <li>)
    "p",                  # nested paragraphs → new line per <p>
}