"""
Data preprocessing and normalization module for entity resolution.
Provides robust text normalization for business names, addresses, and open-set countries.
Preserves original values while producing normalized representations and extracted entities (tokens, numbers, postal codes).
"""
import re
import unicodedata
from typing import Set, Tuple, Dict, Any, Optional
import pandas as pd

# ── Legal Suffix Dictionary & Regex ──────────────────────────────────────────
# Standardize various legal suffix variants to canonical forms or strip them
LEGAL_SUFFIX_REPLACEMENTS = [
    (r"\bprivate\s+limited\b", "pvt ltd"),
    (r"\bpvt\.?\s*ltd\.?\b", "pvt ltd"),
    (r"\bcorporation\b", "corp"),
    (r"\bincorporated\b", "inc"),
    (r"\blimited\s+liability\s+company\b", "llc"),
    (r"\blimited\s+liability\s+partnership\b", "llp"),
    (r"\blimited\b", "ltd"),
    (r"\bcompany\b", "co"),
]

LEGAL_SUFFIXES_TO_STRIP = [
    r"\bpvt\s+ltd\b",
    r"\bltd\b",
    r"\binc\b",
    r"\bcorp\b",
    r"\bcorporation\b",
    r"\bllc\b",
    r"\bllp\b",
    r"\bplc\b",
    r"\blp\b",
    r"\bco\b",
    r"\bgmbh\b",
    r"\bsa\b",
    r"\bsrl\b",
    r"\bpty\b",
    r"\benterprises?\b",
    r"\bservices?\b",
    r"\bsolutions?\b",
    r"\bsystems?\b",
    r"\btechnolog(?:y|ies)\b",
    r"\bgroup\b",
    r"\bholdings?\b",
    r"\bassociates?\b",
]
_STRIP_SUFFIX_PATTERN = re.compile(r"\b(?:" + "|".join(LEGAL_SUFFIXES_TO_STRIP) + r")\b", re.IGNORECASE)

# ── Address Abbreviations & Street Types ─────────────────────────────────────
ADDR_ABBREVS = {
    r"\bstreet\b": "st",
    r"\bavenue\b": "ave",
    r"\bdrive\b": "dr",
    r"\broad\b": "rd",
    r"\bboulevard\b": "blvd",
    r"\blane\b": "ln",
    r"\bcourt\b": "ct",
    r"\bcircle\b": "cir",
    r"\bparkway\b": "pkwy",
    r"\bplace\b": "pl",
    r"\bsuite\b": "ste",
    r"\bapartment\b": "apt",
    r"\bunit\b": "unit",
    r"\bfloor\b": "fl",
    r"\bnorth\b": "n",
    r"\bsouth\b": "s",
    r"\beast\b": "e",
    r"\bwest\b": "w",
    r"\bhighway\b": "hwy",
    r"\broute\b": "rt",
}

# Regex for postal/PIN code extraction:
# US zip (5 or 5-4 digits), Indian PIN (6 digits), UK/Canada alphanumeric
POSTAL_CODE_RE = re.compile(r"\b(?:\d{5}(?:-\d{4})?|\d{6}|[A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d)\b")
NUMBER_RE = re.compile(r"\b\d+\b")

def normalize_unicode(text: str) -> str:
    """NFKD normalization and strip combining diacritics/accents."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in nfkd if not unicodedata.combining(c))

def normalize_whitespace(text: str) -> str:
    """Collapses consecutive whitespace to a single space and strips ends."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()

def remove_punctuation(text: str) -> str:
    """Replaces punctuation with space, keeping alphanumeric characters."""
    if not text:
        return ""
    # Keep alphanumeric and spaces
    return re.sub(r"[^\w\s]", " ", str(text))

def normalize_business_name(name: str) -> Tuple[str, str]:
    """
    Normalizes a business name according to project specifications.
    
    Returns:
        (norm_name, name_no_suffix)
        - norm_name: lowercase, & -> and, canonicalized legal suffixes, clean punctuation
        - name_no_suffix: normalized name with common legal suffixes completely removed
    """
    if not name or pd.isna(name):
        return "", ""
        
    s = normalize_unicode(str(name)).lower()
    
    # Normalize & to and
    s = re.sub(r"\s*&\s*", " and ", s)
    
    # URL extraction if name contains domain
    url_match = re.match(r"^(?:https?://)?(?:www\.)?([a-zA-Z0-9][a-zA-Z0-9-]*)(?:\.[a-z]{2,})+(?:/.*)?$", s.strip())
    if url_match:
        s = url_match.group(1).replace("-", " ")
        
    # Canonicalize legal suffixes (Corporation -> corp, Limited -> ltd, Private Limited -> pvt ltd)
    for pattern, repl in LEGAL_SUFFIX_REPLACEMENTS:
        s = re.sub(pattern, repl, s)
        
    # Remove unnecessary punctuation and clean whitespace
    s = remove_punctuation(s)
    norm_name = normalize_whitespace(s)
    
    # Create name without legal suffix
    name_no_suffix = _STRIP_SUFFIX_PATTERN.sub(" ", norm_name)
    name_no_suffix = normalize_whitespace(name_no_suffix)
    if not name_no_suffix:
        name_no_suffix = norm_name
        
    return norm_name, name_no_suffix

def normalize_address(address: str) -> Tuple[str, Set[str], Set[str]]:
    """
    Normalizes business address and extracts key tokens, numbers, and postal codes.
    
    Returns:
        (norm_address, numbers_set, postal_codes_set)
    """
    if not address or pd.isna(address):
        return "", set(), set()
        
    raw = normalize_unicode(str(address))
    
    # Extract postal codes before stripping punctuation
    postal_matches = POSTAL_CODE_RE.findall(raw)
    postal_codes = {p.replace(" ", "").lower() for p in postal_matches}
    
    s = raw.lower()
    
    # Remove # markers and noise
    s = re.sub(r"#+\s*", "", s)
    s = re.sub(r"\bpo\s+box\s+\d+\b", "", s)
    s = re.sub(r"\bpmb\s+\d+\b", "", s)
    
    # Standardize street abbreviations
    for pattern, repl in ADDR_ABBREVS.items():
        s = re.sub(pattern, repl, s)
        
    # Extract numeric tokens (house numbers, suite numbers)
    numbers = set(NUMBER_RE.findall(s))
    
    # Remove punctuation & normalize whitespace
    s = remove_punctuation(s)
    norm_address = normalize_whitespace(s)
    
    return norm_address, numbers, postal_codes

def normalize_country(country: str) -> str:
    """
    Open-set country normalization.
    Preserves open-set country names (e.g. US, India, France, Germany, etc.).
    """
    if not country or pd.isna(country):
        return ""
    c = normalize_unicode(str(country)).strip().lower()
    return c

def extract_tokens(text: str, min_len: int = 2) -> Set[str]:
    """Tokenizes string into meaningful word tokens."""
    if not text:
        return set()
    return {t for t in text.split() if len(t) >= min_len}

def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocesses a DataFrame containing entity_id, business_name, business_address, country.
    Adds normalized fields without destroying the original fields.
    """
    res = df.copy()
    
    norm_names = []
    names_no_suffix = []
    norm_addresses = []
    numbers_list = []
    postal_list = []
    norm_countries = []
    
    for _, row in df.iterrows():
        bname = row.get("business_name", "")
        baddr = row.get("business_address", "")
        bctry = row.get("country", "")
        
        n_name, n_nosuf = normalize_business_name(bname)
        n_addr, nums, postals = normalize_address(baddr)
        n_ctry = normalize_country(bctry)
        
        norm_names.append(n_name)
        names_no_suffix.append(n_nosuf)
        norm_addresses.append(n_addr)
        numbers_list.append(" ".join(sorted(nums)))
        postal_list.append(" ".join(sorted(postals)))
        norm_countries.append(n_ctry)
        
    res["norm_name"] = norm_names
    res["name_no_suffix"] = names_no_suffix
    res["norm_address"] = norm_addresses
    res["address_numbers"] = numbers_list
    res["postal_codes"] = postal_list
    res["norm_country"] = norm_countries
    
    return res
