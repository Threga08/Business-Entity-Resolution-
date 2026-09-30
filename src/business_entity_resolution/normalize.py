"""
Normalization utilities for business name, address, and country fields.
All normalizers are deterministic and preserve original values.
"""
import re
import unicodedata
from typing import Tuple


# ── Company suffix patterns ──────────────────────────────────────────────
COMPANY_SUFFIXES = [
    # English legal suffixes
    r"\bprivate\s+limited\b",
    r"\bpvt\.?\s*ltd\.?\b",
    r"\bpvt\b",
    r"\bltd\.?\b",
    r"\blimited\b",
    r"\bllc\b",
    r"\bllp\b",
    r"\binc\.?\b",
    r"\bcorp\.?\b",
    r"\bcorporation\b",
    r"\blp\b",
    r"\bplc\b",
    r"\bnpc\b",
    r"\bopc\b",
    r"\bco\.?\b",
    r"\bcompany\b",
    # Business type words
    r"\benterprises?\b",
    r"\bservices?\b",
    r"\bsolutions?\b",
    r"\bsystems?\b",
    r"\btechnolog(?:y|ies)\b",
    r"\btech\b",
    r"\bgroup\b",
    r"\bholdings?\b",
    r"\bassociates?\b",
    r"\bpartners?\b",
    r"\binternational\b",
    r"\bglobal\b",
    r"\bindia\b",
    r"\bdba\b",
    r"\bformerly\b",
    r"\btrading\b",
    r"\bventures?\b",
    r"\bindustries?\b",
    r"\bmanufacturing\b",
    r"\bdistributors?\b",
    r"\bproprietorship\b",
    r"\bproprietor\b",
    r"\bproprietors\b",
    r"\bimports?\s+exports?\b",
    r"\bexports?\b",
    r"\bimports?\b",
]

_SUFFIX_PATTERN = re.compile(
    "|".join(COMPANY_SUFFIXES), re.IGNORECASE
)

# US state abbreviation to full-name mapping
US_STATE_ABBREV = {
    "AL": "alabama", "AK": "alaska", "AZ": "arizona", "AR": "arkansas",
    "CA": "california", "CO": "colorado", "CT": "connecticut", "DE": "delaware",
    "FL": "florida", "GA": "georgia", "HI": "hawaii", "ID": "idaho",
    "IL": "illinois", "IN": "indiana", "IA": "iowa", "KS": "kansas",
    "KY": "kentucky", "LA": "louisiana", "ME": "maine", "MD": "maryland",
    "MA": "massachusetts", "MI": "michigan", "MN": "minnesota", "MS": "mississippi",
    "MO": "missouri", "MT": "montana", "NE": "nebraska", "NV": "nevada",
    "NH": "new hampshire", "NJ": "new jersey", "NM": "new mexico", "NY": "new york",
    "NC": "north carolina", "ND": "north dakota", "OH": "ohio", "OK": "oklahoma",
    "OR": "oregon", "PA": "pennsylvania", "RI": "rhode island", "SC": "south carolina",
    "SD": "south dakota", "TN": "tennessee", "TX": "texas", "UT": "utah",
    "VT": "vermont", "VA": "virginia", "WA": "washington", "WV": "west virginia",
    "WI": "wisconsin", "WY": "wyoming", "DC": "district of columbia",
}
US_STATE_FULL_TO_ABBREV = {v: k.lower() for k, v in US_STATE_ABBREV.items()}

# Address abbreviations
ADDR_ABBREVS = {
    r"\bstreet\b": "st",
    r"\bst\b": "st",
    r"\bavenue\b": "ave",
    r"\bave\b": "ave",
    r"\bdrive\b": "dr",
    r"\bdr\b": "dr",
    r"\broad\b": "rd",
    r"\brd\b": "rd",
    r"\bboulevard\b": "blvd",
    r"\bblvd\b": "blvd",
    r"\blane\b": "ln",
    r"\bln\b": "ln",
    r"\bcourt\b": "ct",
    r"\bct\b": "ct",
    r"\bcircle\b": "cir",
    r"\bparkway\b": "pkwy",
    r"\bpkwy\b": "pkwy",
    r"\bplace\b": "pl",
    r"\bpl\b": "pl",
    r"\bsuite\b": "ste",
    r"\bste\b": "ste",
    r"\bapartment\b": "apt",
    r"\bapt\b": "apt",
    r"\bunit\b": "unit",
    r"\bfloor\b": "fl",
    r"\bfl\b": "fl",
    r"\bnorth\b": "n",
    r"\bsouth\b": "s",
    r"\beast\b": "e",
    r"\bwest\b": "w",
    r"\btownship\b": "twp",
    r"\bcity\b": "city",
}


def normalize_unicode(text: str) -> str:
    """NFKD normalization + strip combining marks for accent removal."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_whitespace(text: str) -> str:
    """Collapse multiple whitespace to single space and strip."""
    return re.sub(r"\s+", " ", text).strip()


def remove_punctuation(text: str) -> str:
    """Remove punctuation except apostrophes in words."""
    # Keep alphanumeric, spaces, and apostrophes within words
    text = re.sub(r"[^\w\s']", " ", text)
    return normalize_whitespace(text)


def extract_url_name(text: str) -> str:
    """If text looks like a URL/domain, extract the business name part."""
    stripped = text.strip()
    # Match patterns like businessname.com, www.business.com/path
    url_pattern = re.match(
        r"^(?:https?://)?(?:www\.)?([a-zA-Z0-9][a-zA-Z0-9-]*)(?:\.[a-z]{2,})+(?:/.*)?$",
        stripped,
    )
    if url_pattern:
        return url_pattern.group(1).replace('-', ' ')
    return text


def normalize_business_name(name: str) -> str:
    """
    Normalize a business name:
    1. Unicode normalize
    2. Lowercase
    3. Extract URL-based names
    4. Remove common company suffixes
    5. Remove punctuation
    6. Collapse whitespace
    """
    if not name or not name.strip():
        return ""

    result = normalize_unicode(name)
    result = result.lower()

    # If contains | separator, take the first part (before URL info)
    if "|" in result:
        result = result.split("|")[0].strip()

    # Extract URL-based names
    result = extract_url_name(result)

    # Remove common suffixes
    result = _SUFFIX_PATTERN.sub(" ", result)

    # Remove punctuation
    result = remove_punctuation(result)

    # Collapse whitespace
    result = normalize_whitespace(result)

    return result


def normalize_address(address: str) -> str:
    """
    Normalize an address:
    1. Unicode normalize
    2. Lowercase
    3. Standardize abbreviations
    4. Remove # and other noise
    5. Collapse whitespace
    """
    if not address or not address.strip():
        return ""

    result = normalize_unicode(address)
    result = result.lower()

    # Remove # markers and PO Box prefixes
    result = re.sub(r"#+\s*", "", result)
    result = re.sub(r"\bpo\s+box\s+\d+\b", "", result)
    result = re.sub(r"\bpmb\s+\d+\b", "", result)

    # Remove unit/apt/suite numbers for matching purposes
    result = re.sub(r"\b(?:unit|apt|suite|ste|apartment|fl|floor)\s*\.?\s*\w*\b", "", result)

    # Standardize street type abbreviations
    for pattern, replacement in ADDR_ABBREVS.items():
        result = re.sub(pattern, replacement, result)

    # Normalize state names (US)
    for full_name, abbrev in US_STATE_FULL_TO_ABBREV.items():
        result = re.sub(r"\b" + re.escape(full_name) + r"\b", abbrev, result)

    # Remove punctuation
    result = remove_punctuation(result)

    # Collapse whitespace
    result = normalize_whitespace(result)

    return result


def extract_name_tokens(normalized_name: str) -> set:
    """Extract meaningful tokens from a normalized business name."""
    if not normalized_name:
        return set()
    tokens = normalized_name.split()
    # Filter out very short tokens (likely noise)
    return {t for t in tokens if len(t) >= 2}


def extract_address_tokens(normalized_address: str) -> set:
    """Extract tokens from a normalized address."""
    if not normalized_address:
        return set()
    return set(normalized_address.split())


def normalize_record(
    name: str, address: str, country: str
) -> Tuple[str, str, str, set, set]:
    """
    Normalize a full record.

    Returns:
        (norm_name, norm_address, country, name_tokens, address_tokens)
    """
    norm_name = normalize_business_name(name)
    norm_addr = normalize_address(address)
    name_tokens = extract_name_tokens(norm_name)
    addr_tokens = extract_address_tokens(norm_addr)
    return norm_name, norm_addr, country, name_tokens, addr_tokens
