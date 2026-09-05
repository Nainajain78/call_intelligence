"""
Step 7: Date resolution -- deterministic, never LLM arithmetic.
"""
from __future__ import annotations
import re
from datetime import date, datetime, timedelta
from typing import Optional
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse as dateutil_parse

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _next_weekday(base: date, weekday_name: str) -> date:
    target = WEEKDAYS.index(weekday_name.lower())
    days_ahead = (target - base.weekday()) % 7
    days_ahead = days_ahead or 7
    return base + timedelta(days=days_ahead)


def resolve_date_phrase(phrase: Optional[str], call_date: date) -> Optional[date]:
    if not phrase:
        return None
    p = phrase.strip().lower()

    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+of\s+next\s+month", p)
    if m:
        day = int(m.group(1))
        target_month = base_next_month(call_date)
        return safe_date(target_month.year, target_month.month, day)

    m = re.search(r"\bthe\s+(\d{1,2})(?:st|nd|rd|th)?\b", p)
    if m and "next month" not in p:
        day = int(m.group(1))
        candidate = safe_date(call_date.year, call_date.month, day)
        if candidate and candidate < call_date:
            nm = base_next_month(call_date)
            candidate = safe_date(nm.year, nm.month, day)
        return candidate

    if p == "next month":
        return base_next_month(call_date)

    for wd in WEEKDAYS:
        if wd in p:
            target = _next_weekday(call_date, wd)
            if "next " + wd in p:
                target += timedelta(days=7)
            return target

    if "tomorrow" in p:
        return call_date + timedelta(days=1)
    if "today" in p or "end of call" in p:
        return call_date
    m = re.search(r"in\s+(\d+)\s+day", p)
    if m:
        return call_date + timedelta(days=int(m.group(1)))
    m = re.search(r"in\s+(\d+)\s+week", p)
    if m:
        return call_date + timedelta(weeks=int(m.group(1)))

    # Fallback: dateutil needs a full datetime as `default`, not a bare
    # date, because fuzzy parsing tries to set hour/minute/second on it.
    try:
        default_dt = datetime.combine(call_date, datetime.min.time())
        parsed = dateutil_parse(phrase, default=default_dt, fuzzy=True)
        return parsed.date()
    except (ValueError, OverflowError, TypeError):
        return None


def base_next_month(d: date) -> date:
    return d + relativedelta(months=1)


def safe_date(year: int, month: int, day: int) -> Optional[date]:
    try:
        return date(year, month, day)
    except ValueError:
        return None
