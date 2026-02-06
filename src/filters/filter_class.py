# --- CLASS-LEVEL FILTERS: exact class names --------------------------------
SKIP_CLASS = {
    # Global navigation & chrome
    "nav",              # main navigation container
    "navbar",           # navigation bar (e.g. Bootstrap)
    "menu",             # generic menu container
    "breadcrumbs",      # breadcrumb navigation trail
    "breadcrumb",       # single breadcrumb trail
    "pager",            # prev/next pager ("Older posts")
    "pagination",       # numbered pagination bar

    # Layout / sidebars / widgets
    "sidebar",          # generic sidebar container
    "widget",           # generic widget box

    # Table of contents
    "toc",              # table of contents container
    "table-of-contents",# explicit TOC name

    # WordPress-specific widgets
    "widget_recent_entries",   # recent posts widget
    "widget_categories",       # categories list widget
    "widget_archive",          # archive list widget
    "widget_meta",             # meta widget (login, RSS...)

    # Wikipedia-specific meta / navigation / references
    "navbox",                  # large navigation boxes ("related topics")
    "mw-editsection",          # [edit] links next to headings
    "printfooter",             # "Retrieved from..." footer
    "vector-jumplink",         # jump links ("Jump to navigation")
    "mw-jump-link",            # same as above
    "vector-toc-text",         # text in TOC entries
    "vector-toc-link",         # TOC link wrapper

    "noprint",                 # hidden on print/mobile
    "reflist",                 # wrapper around references list
    "mw-references-wrap",      # references wrapper
    "references",              # <ol class="references">
    "reference",               # individual reference
    "mw-cite-backlink",        # [↑] back-link in footnotes

    "sistersitebox",           # sister project box
    "side-box",                # side info box
    "side-box-text",           # text inside side box
    "hatnote",                 # "For other uses, see…"

    "infobox",                 # general infobox (persons, companies)
    "ib-company",              # company infobox
    "vcard",                   # vCard-style infobox data

    "catlinks",                # category links box
    "mw-normal-catlinks",      # normal category list
    "mw-hidden-catlinks",      # hidden category list

    "mw-authority-control",    # authority control data box

    # maybe:
    "site-footer", 
    "page-footer",
    "site-nav",
    "extra-services",
    "fb-comments",
}

# Class name prefixes that usually indicate boilerplate containers
SKIP_CLASS_PREFIX = {
    # Navigation & chrome prefixes
    "nav-",            # nav-main, nav-primary
    "navbar-",         # navbar-top, navbar-fixed
    "menu-",           # menu-main, menu-footer
    "main-nav",        # main-nav, main-nav-inner
    "primary-nav",     # primary-nav-list
    "secondary-nav",   # secondary-nav-list

    # Layout & sidebars / widgets
    "sidebar-",        # sidebar-left, sidebar-right, sidebar-nav
    "widget-",         # widget-area, widget-title

    # Footer-related
    "footer-",         # footer-nav, footer-links

    # Advertising & promotions
    "ad-",             # ad-slot, ad-banner
    "ads-",            # ads-top, ads-sidebar
    "banner-",         # banner-ad, banner-cookie
    "promo-",          # promo-box, promo-teaser

    # Cookie / GDPR / consent
    "cookie-",         # cookie-bar, cookie-banner
    "gdpr-",           # gdpr-banner, gdpr-consent
    "consent-",        # consent-dialog

    # Modals / overlays / popups
    "modal-",          # modal-dialog, modal-content
    "popup-",          # popup-wrapper, popup-content
    "overlay-",        # overlay-bg, overlay-backdrop

    # Newsletter / subscriptions / accounts
    "newsletter-",     # newsletter-box, newsletter-signup
    "subscribe-",      # subscribe-box, subscribe-cta
    "subscription-",   # subscription-widget
    "login-",          # login-panel
    "signup-",         # signup-panel
    "register-",       # register-panel

    # Related content / social / comments
    "related-",        # related-posts, related-articles
    "social-",         # social-links, social-bar
    "share-",          # share-buttons
    "comment-",        # comment-form, comment-meta
    "comments-",       # comments-area

    # Tables of contents
    "toc-",            # toc-list, toc-container
}
# High-signal substrings inside class names that indicate non-content UI
SKIP_CLASS_CONTAINS = {  # CAREFUL: CHECK FOR FALSE-POSITIVE!
    # Legal / cookie / GDPR
    "cookie",          # cookiebanner, cookie-consent
    "gdpr",            # gdpr-consent, gdpr-notice
    "consent",         # consent-banner, consent-popup

    # Advertising & sponsorship
    "advert",          # advert, advertisement
    "sponsor",         # sponsor, sponsored-content
    "promotion",       # promotion, promotional
    "promo",           # promo, promo-box

    # Newsletter / subscriptions / access
    "newsletter",      # newsletter, newsletter-signup
    "subscribe",       # subscribe, subscribe-box
    "subscription",    # subscription-widget
    "login",           # login-box, login-link
    "signup",          # signup-link, signup-modal
    "register",        # register-box, user-register

    # Related / recommendations / teasers
    "related",         # related-posts, related-articles
    "recommendation",  # recommendation-list, recommendations
    "teaser",          # teaser, teaser-list
    "tagcloud",        # tagcloud, tag-cloud

    # Social / sharing / comments / ratings
    "social",          # social, social-icons
    "share",           # share, share-buttons
    "disqus",          # disqus widgets
    "rating",          # rating, rating-stars
    "review",          # review, reviews, review-stars
}