"""Shared half-hour clock parsing for event and timetable modules."""

EVENT_MISSING_TIME = '請填寫半小時單位的時間，例如 09:00 或 09:30。'
EVENT_INVALID_TIME = '時間須為 00:00–24:00，並以半小時為單位。'
TIMETABLE_MISSING_TIME = '請填寫時間，例如 18:00 或 18:30。'
TIMETABLE_INVALID_TIME = '時間以半小時為單位，範圍為 00:00–24:00。'


def parse_clock(value, missing_message, invalid_message):
    """Return minutes since midnight, preserving the caller's error wording."""
    try:
        hour, minute = map(int, value.split(':'))
    except (ValueError, AttributeError):
        raise ValueError(missing_message) from None
    if not 0 <= hour <= 24 or minute not in (0, 30) or (hour == 24 and minute):
        raise ValueError(invalid_message)
    return hour * 60 + minute
