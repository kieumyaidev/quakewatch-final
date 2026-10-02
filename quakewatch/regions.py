US_STATE_CODES = {"CA": "California", "NV": "Nevada", "WA": "Washington", "OR": "Oregon", "UT": "Utah", "MX": "Mexico"}


def region_from_place(place: str | None) -> str:
    if not place:
        return "Unknown"
    region = place.rsplit(",", 1)[-1].strip()
    if " of " in region and "," not in place:
        region = region.rsplit(" of ", 1)[-1].strip()
    return US_STATE_CODES.get(region, region)
