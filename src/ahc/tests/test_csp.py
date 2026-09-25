import pytest


@pytest.mark.integration
@pytest.mark.django_db
class TestCSPHeaders:
    def test_report_only_header_present(self, client):
        response = client.get("/")
        assert "Content-Security-Policy-Report-Only" in response.headers

    def test_report_only_default_src_self(self, client):
        response = client.get("/")
        header = response.headers.get("Content-Security-Policy-Report-Only", "")
        assert "default-src 'self'" in header

    def test_report_only_no_unsafe_scripts(self, client):
        response = client.get("/")
        header = response.headers.get("Content-Security-Policy-Report-Only", "")
        assert "script-src 'self'" in header
        assert "'unsafe-inline'" not in header.split("script-src")[1].split(";")[0]
