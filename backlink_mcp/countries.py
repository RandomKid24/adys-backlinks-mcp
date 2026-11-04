"""Country data used to localise footprints, directory filtering, phone formatting and schema.
Add a country by adding a line - nothing else needs to change."""
from __future__ import annotations

import re

# code: (English name, dialling code, national number length(s), extra aliases)
COUNTRIES: dict[str, tuple[str, str, tuple[int, ...], tuple[str, ...]]] = {
    "IN": ("India", "91", (10,), ("bharat",)),
    "US": ("United States", "1", (10,), ("usa", "america", "united states of america")),
    "CA": ("Canada", "1", (10,), ()),
    "GB": ("United Kingdom", "44", (10,), ("uk", "england", "scotland", "wales", "britain", "great britain")),
    "IE": ("Ireland", "353", (9,), ()),
    "AU": ("Australia", "61", (9,), ()),
    "NZ": ("New Zealand", "64", (8, 9), ()),
    "AE": ("United Arab Emirates", "971", (9,), ("uae", "dubai", "abu dhabi")),
    "SA": ("Saudi Arabia", "966", (9,), ("ksa",)),
    "QA": ("Qatar", "974", (8,), ()),
    "SG": ("Singapore", "65", (8,), ()),
    "MY": ("Malaysia", "60", (9, 10), ()),
    "PH": ("Philippines", "63", (10,), ()),
    "ID": ("Indonesia", "62", (9, 10, 11), ()),
    "TH": ("Thailand", "66", (9,), ()),
    "VN": ("Vietnam", "84", (9,), ()),
    "JP": ("Japan", "81", (10,), ()),
    "PK": ("Pakistan", "92", (10,), ()),
    "BD": ("Bangladesh", "880", (10,), ()),
    "LK": ("Sri Lanka", "94", (9,), ()),
    "NP": ("Nepal", "977", (10,), ()),
    "DE": ("Germany", "49", (10, 11), ("deutschland",)),
    "FR": ("France", "33", (9,), ()),
    "ES": ("Spain", "34", (9,), ()),
    "IT": ("Italy", "39", (9, 10), ()),
    "NL": ("Netherlands", "31", (9,), ("holland",)),
    "BE": ("Belgium", "32", (8, 9), ()),
    "CH": ("Switzerland", "41", (9,), ()),
    "SE": ("Sweden", "46", (9,), ()),
    "PL": ("Poland", "48", (9,), ()),
    "PT": ("Portugal", "351", (9,), ()),
    "ZA": ("South Africa", "27", (9,), ()),
    "NG": ("Nigeria", "234", (10,), ()),
    "KE": ("Kenya", "254", (9,), ()),
    "EG": ("Egypt", "20", (10,), ()),
    "BR": ("Brazil", "55", (10, 11), ("brasil",)),
    "MX": ("Mexico", "52", (10,), ()),
}

# Countries whose numbers keep the leading 0 after the country code (or have no trunk prefix).
KEEP_TRUNK_ZERO = {"IT", "US", "CA"}

# Countries that read naturally with "the" ("across the United States").
WITH_THE = {"US", "GB", "AE", "NL", "PH"}

# Region groups a directory can target instead of one country.
REGIONS: dict[str, set[str]] = {
    "EU": {"DE", "FR", "ES", "IT", "NL", "BE", "SE", "PL", "PT", "IE"},
    "EUROPE": {"DE", "FR", "ES", "IT", "NL", "BE", "SE", "PL", "PT", "IE", "GB", "CH"},
    "GCC": {"AE", "SA", "QA"},
    "ANZ": {"AU", "NZ"},
    "NA": {"US", "CA"},
    "SEA": {"SG", "MY", "PH", "ID", "TH", "VN"},
    "SOUTH_ASIA": {"IN", "PK", "BD", "LK", "NP"},
}


def resolve_country(value: str | None) -> str | None:
    """'India' / 'in' / 'IN' / 'uk' / 'United Kingdom' -> ISO code. Unknown -> None."""
    if not value:
        return None
    v = value.strip().lower()
    for code, (name, _dial, _len, aliases) in COUNTRIES.items():
        if v in (code.lower(), name.lower(), *aliases):
            return code
    return None


def country_name(code_or_name: str | None, article: bool = False) -> str:
    code = resolve_country(code_or_name)
    if not code:
        return code_or_name or ""
    return ("the " if article and code in WITH_THE else "") + COUNTRIES[code][0]


def region_matches(region: str | list[str], code: str | None) -> bool:
    """Does a directory's region ('global', 'IN', 'EU', ['US','CA']) cover this country?"""
    regions = region if isinstance(region, list) else [region]
    for r in regions:
        r = (r or "global").upper()
        if r == "GLOBAL" or (code and (r == code or code in REGIONS.get(r, set()))):
            return True
    return False


def format_phone(raw: str | None, country: str | None) -> tuple[str | None, str | None]:
    """Return (display, e164). Adds the country code when the number is national-length.
    One consistent display format matters more than which format it is."""
    if not raw:
        return None, None
    digits = re.sub(r"\D", "", raw)
    code = resolve_country(country)
    r = raw.strip()
    if r.startswith("00"):
        digits = digits[2:]
    elif code and not r.startswith("+"):
        _name, dial, lengths, _ = COUNTRIES[code]
        if digits.startswith(dial) and len(digits) - len(dial) in lengths:
            pass  # already includes the country code, just without "+"
        elif digits.startswith("0") and code not in KEEP_TRUNK_ZERO:
            digits = dial + digits[1:]  # drop the national trunk "0"
        elif len(digits) in lengths or code in KEEP_TRUNK_ZERO:
            digits = dial + digits
        else:
            return r, None  # can't tell - keep exactly what was given
    e164 = "+" + digits
    # pick the dialling code that prefixes the number (longest match first)
    dial = next((d for d in sorted({c[1] for c in COUNTRIES.values()}, key=len, reverse=True) if digits.startswith(d)), None)
    if not dial:
        return raw.strip(), e164
    rest = digits[len(dial):]
    if dial == "91" and len(rest) == 10:
        disp = f"+91 {rest[:5]} {rest[5:]}"
    elif dial == "1" and len(rest) == 10:
        disp = f"+1 {rest[:3]} {rest[3:6]} {rest[6:]}"
    else:
        head, tail = (rest[:-4], rest[-4:]) if len(rest) > 4 else ("", rest)
        first = len(head) % 3 or 3
        groups = ([head[:first]] + [head[i:i + 3] for i in range(first, len(head), 3)] if head else []) + [tail]
        disp = f"+{dial} " + " ".join(g for g in groups if g)
    return disp, e164
