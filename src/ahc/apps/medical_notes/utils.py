"""Presentation helpers for medical_notes views.

Pure functions — no database access. Database queries belong in selectors.py.
"""

from __future__ import annotations


def build_timeline_base_query(type_of_event: str, tag_name: str) -> str:
    """Build the base query string for timeline filter links.

    Returns a URL query string fragment (without leading '?') combining
    whichever of type_of_event / tag_name are non-empty. Used by
    FullTimelineOfNotes to propagate active filters across paginated links.

    Examples:
        build_timeline_base_query("diet_note", "") -> "type_of_event=diet_note"
        build_timeline_base_query("", "rabies")   -> "tag_name=rabies"
        build_timeline_base_query("", "")         -> ""
    """
    parts = []
    if type_of_event:
        parts.append(f"type_of_event={type_of_event}")
    if tag_name:
        parts.append(f"tag_name={tag_name}")
    return "&".join(parts)
