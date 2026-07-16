"""Canonical percentage and fraction handling for fund data.

Backend ``pct``/``net_value_pct`` fields are percentage points: ``0.59``
means 0.59%, not 59%.  Inside the AI engine every weight is stored as a
fraction, preferably in an explicit ``weight_fraction`` field.  Keeping these
two meanings separate avoids guessing units from the numeric magnitude.
"""

from __future__ import annotations

import math
import re
from typing import Any, Mapping, Optional, Sequence


def to_finite_float(value: Any) -> Optional[float]:
    """Parse a numeric value and reject NaN/Inf instead of propagating it."""

    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip().replace(",", "")
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if not match:
            return None
        number = float(match.group(0))
    return number if math.isfinite(number) else None


def percentage_points_to_fraction(value: Any) -> Optional[float]:
    """Convert a backend percentage-point value to an internal fraction."""

    number = to_finite_float(value)
    if number is None:
        return None
    return number / 100.0


def canonical_fraction(value: Any) -> Optional[float]:
    """Parse an internal fraction without magnitude-based unit guessing.

    Numeric values are already fractions, including gross exposures above
    1.0.  External percentage strings must carry an explicit ``%`` suffix.
    """

    number = to_finite_float(value)
    if number is None:
        return None
    if isinstance(value, str) and "%" in value:
        return number / 100.0
    return number


def first_present_value(row: Mapping[str, Any], keys: Sequence[str]) -> Any:
    """Return the first present, non-null field while preserving numeric zero."""

    for key in keys:
        if key in row and row[key] is not None and row[key] != "":
            return row[key]
    return None


def holding_weight_fraction(row: Mapping[str, Any]) -> Optional[float]:
    """Read one holding weight using the explicit internal unit contract."""

    if "weight_fraction" in row and row["weight_fraction"] is not None:
        return canonical_fraction(row["weight_fraction"])
    raw_percent = first_present_value(
        row,
        ("pct", "net_value_pct", "占净值比例"),
    )
    return percentage_points_to_fraction(raw_percent)


def normalize_backend_holding(row: Mapping[str, Any]) -> dict[str, Any]:
    """Copy a backend holding row and attach its canonical fraction."""

    normalized = dict(row)
    raw_percent = first_present_value(
        row,
        ("pct", "net_value_pct", "占净值比例"),
    )
    normalized["weight_fraction"] = percentage_points_to_fraction(raw_percent)
    return normalized
