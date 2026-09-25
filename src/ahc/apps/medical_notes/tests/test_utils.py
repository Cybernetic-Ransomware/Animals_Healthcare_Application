import pytest

from ahc.apps.medical_notes.utils import build_timeline_base_query


@pytest.mark.unit
class TestBuildTimelineBaseQuery:
    """build_timeline_base_query: pure query-string assembly."""

    def test_both_params(self):
        result = build_timeline_base_query("diet_note", "rabies")
        assert result == "type_of_event=diet_note&tag_name=rabies"

    def test_only_type_of_event(self):
        assert build_timeline_base_query("diet_note", "") == "type_of_event=diet_note"

    def test_only_tag_name(self):
        assert build_timeline_base_query("", "rabies") == "tag_name=rabies"

    def test_both_empty(self):
        assert build_timeline_base_query("", "") == ""
