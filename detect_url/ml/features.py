"""URL-only feature extraction with train/serve parity.

These features are computed from the URL string alone, so the exact same
function is used during training (from dataset/dataset_phishing.csv) and at
inference (on a live URL submitted to the website). No HTML, WHOIS or third
party lookups are involved -- this avoids train/serve skew.
"""
import math
import re
from collections import Counter
from urllib.parse import urlparse

URL_SCHEMES = ("http://", "https://", "ftp://")

SHORTENERS = (
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly",
    "adf.ly", "bit.do", "rebrand.ly", "cutt.ly", "shorte.st", "bc.vc",
    "s.id", "t.ly", "lnkd.in", "fb.me", "j.mp", "su.pr", "po.st",
)

PHISH_HINTS = (
    "login", "signin", "sign-in", "logon", "verify", "verification",
    "update", "confirm", "account", "secure", "security", "banking",
    "bank", "credential", "password", "reset", "suspend", "limited",
    "unusual", "activity", "validate", "auth", "authorize", "support",
    "helpdesk", "billing", "invoice", "warn", "alert", "urgent", "action",
)

BRANDS = (
    "paypal", "amazon", "apple", "google", "microsoft", "netflix",
    "facebook", "instagram", "twitter", "linkedin", "steam", "ebay",
    "chase", "wellsfargo", "bankofamerica", "dropbox", "adobe", "yahoo",
    "outlook", "gmail", "whatsapp", "icici", "hdfc", "sbi", "aadhaar",
)

SUSPICIOUS_TLDS = (
    ".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".work", ".loan",
    ".win", ".racing", ".review", ".country", ".stream", ".link", ".click",
    ".download", ".gdn", ".zip", ".mov", ".icu", ".pw", ".su", ".cn",
)

PATH_EXTENSIONS = (
    ".php", ".html", ".htm", ".asp", ".aspx", ".jsp", ".cgi", ".js",
)


def _normalise(url: str) -> str:
    u = (url or "").strip()
    if not any(u.lower().startswith(s) for s in URL_SCHEMES):
        u = "http://" + u
    return u


def _hostname(parse) -> str:
    return (parse.hostname or "").lower()


def _registered_domain(host: str) -> str:
    """Approximate eTLD+1 without a public suffix list dependency."""
    parts = [p for p in host.split(".") if p]
    if len(parts) < 2:
        return host
    # Handle common two-part public suffixes.
    two = {"co.uk", "org.uk", "com.au", "net.au", "co.in", "com.br", "co.jp"}
    if ".".join(parts[-2:]) in two and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _subdomains(host: str) -> list:
    reg = _registered_domain(host)
    if not reg or not host.endswith(reg):
        return []
    prefix = host[: -(len(reg) + 1)]
    return [p for p in prefix.split(".") if p]


def _words(text: str) -> list:
    return [w for w in re.split(r"[/.\-_?=&%]+", text) if w]


def _word_stats(words: list) -> dict:
    if not words:
        return dict(longest=0, shortest=0, avg=0.0)
    lengths = [len(w) for w in words]
    return dict(
        longest=max(lengths),
        shortest=min(lengths),
        avg=sum(lengths) / len(lengths),
    )


def extract(url: str) -> dict:
    """Return an ordered dict of numeric features for one URL."""
    u = _normalise(url)
    p = urlparse(u)
    host = _hostname(p)
    path = p.path or ""
    query = p.query or ""
    reg = _registered_domain(host)
    subs = _subdomains(host)
    lower = u.lower()
    host_lower = host.lower()

    digits_url = sum(c.isdigit() for c in u)
    digits_host = sum(c.isdigit() for c in host)

    # Longest run of the same character (character repetition).
    repeat = 1
    run = 1
    for i in range(1, len(u)):
        run = run + 1 if u[i] == u[i - 1] else 1
        repeat = max(repeat, run)

    raw_stats = _word_stats(_words(u))
    host_stats = _word_stats(_words(host))
    path_stats = _word_stats(_words(path))

    # Shannon entropy of the domain core -- random looking domains score high.
    core = reg.split(".")[0] if reg else ""
    entropy = 0.0
    if core:
        counts = Counter(core)
        n = len(core)
        entropy = -sum((c / n) * math.log2(c / n) for c in counts.values())

    path_ext = int(any(path.lower().endswith(e) for e in PATH_EXTENSIONS))

    label = "phishing"
    f = {
        "length_url": len(u),
        "length_hostname": len(host),
        "ip": int(bool(re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host))),
        "nb_dots": u.count("."),
        "nb_hyphens": u.count("-"),
        "nb_at": u.count("@"),
        "nb_qm": u.count("?"),
        "nb_and": u.count("&"),
        "nb_eq": u.count("="),
        "nb_underscore": u.count("_"),
        "nb_tilde": u.count("~"),
        "nb_percent": u.count("%"),
        "nb_slash": u.count("/"),
        "nb_star": u.count("*"),
        "nb_colon": u.count(":"),
        "nb_comma": u.count(","),
        "nb_semicolumn": u.count(";"),
        "nb_dollar": u.count("$"),
        "nb_space": u.count(" "),
        "nb_www": lower.count("www"),
        "nb_com": lower.count(".com"),
        "nb_dslash": lower.count("//"),
        "http_in_path": int("http" in path.lower()),
        "https_token": int("https" in lower),
        "ratio_digits_url": digits_url / len(u) if u else 0.0,
        "ratio_digits_host": digits_host / len(host) if host else 0.0,
        "punycode": int("xn--" in lower or "punycode" in lower),
        "port": int(p.port is not None),
        "tld_in_path": int(any(t in path.lower() for t in SUSPICIOUS_TLDS)),
        "tld_in_subdomain": int(any(t in s.lower() for s in subs for t in SUSPICIOUS_TLDS)),
        "abnormal_subdomain": int(len(subs) >= 3),
        "nb_subdomains": len(subs),
        "prefix_suffix": int("-" in host),
        "random_domain": int(entropy >= 3.6 and any(c.isdigit() for c in core)),
        "shortening_service": int(any(host_lower == s or host_lower.endswith("." + s) for s in SHORTENERS)),
        "path_extension": path_ext,
        "length_words_raw": max(raw_stats.values()),
        "char_repeat": repeat,
        "shortest_words_raw": raw_stats["shortest"],
        "shortest_word_host": host_stats["shortest"],
        "shortest_word_path": path_stats["shortest"],
        "longest_words_raw": raw_stats["longest"],
        "longest_word_host": host_stats["longest"],
        "longest_word_path": path_stats["longest"],
        "avg_words_raw": raw_stats["avg"],
        "avg_word_host": host_stats["avg"],
        "avg_word_path": path_stats["avg"],
        "phish_hints": sum(1 for k in PHISH_HINTS if k in lower),
        "domain_in_brand": int(any(b in reg for b in BRANDS)),
        "brand_in_subdomain": int(any(b in s.lower() for s in subs for b in BRANDS)),
        "brand_in_path": int(any(b in path.lower() for b in BRANDS)),
        "suspecious_tld": int(any(host_lower.endswith(t) for t in SUSPICIOUS_TLDS)),
        "domain_entropy": entropy,
        "query_length": len(query),
        "nb_params": len([x for x in query.split("&") if x]),
        "has_at_sign": int("@" in u),
        "digit_letter_transition": len(re.findall(r"(?=[a-z])(?<=\d)|(?<=\d)(?=[a-z])", lower)),
    }
    return f


FEATURE_NAMES = list(extract("http://example.com").keys())
