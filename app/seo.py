import json
from app.i18n import LANGS, lang_url


def alternates(base_url: str, logical_path: str):
    """Return list of (hreflang, url) tuples including x-default."""
    alts = [(lang, base_url + lang_url(lang, logical_path)) for lang in LANGS]
    alts.append(("x-default", base_url + logical_path))
    return alts


def canonical_url(base_url: str, lang: str, logical_path: str) -> str:
    return base_url + lang_url(lang, logical_path)


def breadcrumb_jsonld(base_url: str, lang: str, crumbs: list) -> str:
    """
    crumbs: list of (name, url) tuples in breadcrumb order (home not included).
    Returns JSON-LD script content (no <script> tags).
    """
    items = [
        {
            "@type": "ListItem",
            "position": i + 1,
            "name": name,
            "item": base_url + lang_url(lang, url),
        }
        for i, (name, url) in enumerate(crumbs)
    ]
    return json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": items,
        },
        ensure_ascii=False,
        indent=1,
    )
