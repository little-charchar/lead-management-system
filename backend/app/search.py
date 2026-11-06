"""Shared search-term normalization for legal region aliases."""

REGION_SEARCH_ALIASES = {
    "NY": "NEW YORK",
    "NEW YORK": "NY",
    "CA": "CALIFORNIA",
    "CALIFORNIA": "CA",
    "ON": "ONTARIO",
    "ONTARIO": "ON",
    "TX": "TEXAS",
    "TEXAS": "TX",
}


def region_search_terms(query: str) -> tuple[str, ...]:
    """Return region-equivalent terms for complete or partial region searches."""
    normalized = query.strip().upper()
    terms = [query]
    for abbreviation, full_name in REGION_SEARCH_ALIASES.items():
        if normalized and (
            normalized in abbreviation or normalized in full_name
        ):
            terms.extend((abbreviation, full_name))
    return tuple(dict.fromkeys(terms))
