from datetime import datetime


def parse_datetime(value, date_only=False):
    """Parses datetime-local ('%Y-%m-%dT%H:%M') or plain date strings. Returns None if invalid/empty."""
    if not value:
        return None
    formats = ["%Y-%m-%d"] if date_only else ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
