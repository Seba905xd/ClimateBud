"""Common helper functions for ClimateBud."""

import re
from datetime import datetime, timedelta
from typing import Tuple, Optional

import config


def format_date(date: datetime, format_str: str = "%Y-%m-%d") -> str:
    """Format a datetime object as a string."""
    return date.strftime(format_str)


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse a date string into a datetime object."""
    formats = ["%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%B %d, %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def parse_location(location_str: str) -> dict:
    """Parse a location string into components (county, state, etc.)."""
    location = {
        "county": None,
        "state": None,
        "zip_code": None,
    }

    # Check for state abbreviation
    state_pattern = r"\b([A-Z]{2})\b"
    state_match = re.search(state_pattern, location_str.upper())
    if state_match:
        location["state"] = state_match.group(1)

    # Check for ZIP code
    zip_pattern = r"\b(\d{5})\b"
    zip_match = re.search(zip_pattern, location_str)
    if zip_match:
        location["zip_code"] = zip_match.group(1)

    # Check for county (word before "County")
    county_pattern = r"(\w+)\s+County"
    county_match = re.search(county_pattern, location_str, re.IGNORECASE)
    if county_match:
        location["county"] = county_match.group(1)

    return location


def validate_date_range(start_date: datetime, end_date: datetime) -> Tuple[bool, str]:
    """Validate that a date range is acceptable."""
    if start_date > end_date:
        return False, "Start date must be before end date"

    max_range = timedelta(days=config.MAX_TIME_RANGE_DAYS)
    if end_date - start_date > max_range:
        return False, f"Date range cannot exceed {config.MAX_TIME_RANGE_DAYS} days"

    if end_date > datetime.now():
        return False, "End date cannot be in the future"

    return True, ""


def sanitize_text(text: str) -> str:
    """Sanitize text for safe display and storage."""
    # Remove potential HTML/script tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_state_fips(state_abbrev: str) -> Optional[str]:
    """Get FIPS code for a state abbreviation."""
    fips_codes = {
        "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
        "CO": "08", "CT": "09", "DE": "10", "FL": "12", "GA": "13",
        "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19",
        "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24",
        "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29",
        "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34",
        "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
        "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45",
        "SD": "46", "TN": "47", "TX": "48", "UT": "49", "VT": "50",
        "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56",
    }
    return fips_codes.get(state_abbrev.upper())


def get_county_fips(state: str, county: str) -> Optional[str]:
    """Get FIPS code for a county. Returns state+county FIPS."""
    # Common counties - expand as needed
    county_fips = {
        ("AL", "BALDWIN"): "01003",
        ("AL", "MOBILE"): "01097",
        ("CA", "LOS ANGELES"): "06037",
        ("CA", "SAN FRANCISCO"): "06075",
        ("FL", "MIAMI-DADE"): "12086",
        ("TX", "HARRIS"): "48201",
    }
    key = (state.upper(), county.upper())
    return county_fips.get(key)


def severity_color(severity: str) -> str:
    """Return a color code for violation severity."""
    colors = {
        "high": "#FF4444",
        "medium": "#FFA500",
        "low": "#FFFF00",
        "unknown": "#CCCCCC",
    }
    return colors.get(severity.lower(), colors["unknown"])


def format_number(num: float, decimals: int = 2) -> str:
    """Format a number with thousands separators."""
    if num >= 1_000_000:
        return f"{num/1_000_000:.{decimals}f}M"
    elif num >= 1_000:
        return f"{num/1_000:.{decimals}f}K"
    else:
        return f"{num:.{decimals}f}"
