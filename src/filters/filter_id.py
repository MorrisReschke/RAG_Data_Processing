# --- ID-LEVEL FILTERS: exact IDs ------------------------------------------
SKIP_ID = {
    # Navigation / layout
    "nav",                 # main navigation
    "navbar",              # navigation bar
    "header-nav",          # header navigation region
    "site-nav",            # site-wide navigation
    "sidebar",             # generic sidebar
    "footer",              # global footer
    "site-footer",         # site-wide footer

    # Utility / table of contents
    "toc",                 # table of contents
    "table-of-contents",   # explicit TOC id
    "back-to-top",         # scroll-to-top button
    "scroll-top",          # scroll-to-top link

    # Wikipedia-specific IDs
    "wmde-banner",              # fundraising banner
    "wmde-campaign-parameters", # WMDE campaign parameters
    "toc-References",           # TOC entry for references
    "toc-References-sublist",   # nested references list in TOC
    "catlinks",                 # category links box
    "mw-normal-catlinks",       # normal category list
    "mw-hidden-catlinks",       # hidden category list
    "references",               # <h2 id="References">
    "external_links",           # <h2 id="External_links">

    # optional
    "site-header",
    "page-footer",

    # Wikipedia-specific IDs
    "centralnotice",            # CentralNotice container (campaign banners like "Wiki Loves Folklore")
    "sitenotice",               # outer notice wrapper that contains centralNotice
    "wlf2026-wrapper",          # specific campaign wrapper (optional but cheap)
}
# ID prefixes that usually indicate non-content containers
SKIP_ID_PREFIX = {
    "nav-",             # nav-main, nav-secondary
    "navbar-",          # navbar-top, navbar-fixed
    "menu-",            # menu-main
    "sidebar-",         # sidebar-left, sidebar-right
    "footer-",          # footer-nav, footer-links

    "modal-",           # modal-login
    "popup-",           # popup-newsletter
    "overlay-",         # overlay-bg

    "ad-",              # ad-top, ad-bottom
    "ads-",             # ads-sidebar
}
# High-signal substrings inside IDs that indicate boilerplate
SKIP_ID_CONTAINS = {  # CAREFUL: CHECK FOR FALSE-POSITIVE!
    "cookie",           # cookie-banner, cookie-consent
    "gdpr",             # gdpr-consent
    "consent",          # consent-banner
    "advert",           # advert, advertisement
    "sponsor",          # sponsor, sponsored
    "banner",           # banner-cookie, tracking-banner
    "newsletter",       # newsletter, newsletter-signup
    "subscribe",        # subscribe, subscribe-box
    "subscription",     # subscription-widget
    "social",           # social, social-links
    "share",            # share, share-buttons
    "comment",          # comment, comments, comment-form
    "disqus",           # disqus_thread-like IDs
    "login",            # login, login-form
    "signup",           # signup, signup-form
    "register",         # register, register-form
    "related",          # related, related-posts
    "recommendation",   # recommendation-list
    "teaser",           # teaser, teaser-box
    "tracking",         # tracking-script, tracking-box
}