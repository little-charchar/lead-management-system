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
    """Return region-equivalent terms when a query exactly names a known region."""
    normalized = query.strip().upper()
    alias = REGION_SEARCH_ALIASES.get(normalized)
    return (query, alias) if alias else (query,)
