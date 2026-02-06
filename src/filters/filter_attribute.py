# --- ATTRIBUTE-LEVEL FILTERS (name and value based) -----------------------
# Attributes whose presence alone hides the node
SKIP_ATTR = {
    "hidden",           # <div hidden> – completely hidden from users
}

# Attribute names starting with these prefixes usually mark boilerplate
SKIP_ATTR_PREFIX = {
    "data-ad",      # data-ad, data-ad-slot, data-ad-client
    "data-ads",     # data-ads, data-ads-config
}

# Attribute names containing these substrings usually mark boilerplate
SKIP_ATTR_NAME_CONTAINS = {  # CAREFUL: CHECK FOR FALSE-POSITIVE!
    "cookie",           # data-cookieconsent, data-cookie-banner
    "gdpr",             # data-gdpr-consent
    "consent",          # data-consent-id
    "tracking",         # data-tracking-id
}

# Attribute values containing these substrings usually mark boilerplate
SKIP_ATTR_VALUE_CONTAINS = {  # CAREFUL: CHECK FOR FALSE-POSITIVE!
    "cookie",           # aria-label="Cookie banner"
    "gdpr",             # e.g. "GDPR notice"
    "consent",          # e.g. "Consent dialog"
    "advert",           # "Advertisement"
    "sponsor",          # "Sponsored content"
    "tracking",         # "tracking script"
}