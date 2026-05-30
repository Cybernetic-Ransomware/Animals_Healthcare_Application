import pytest
from django.test import Client, TestCase


@pytest.mark.integration
@pytest.mark.django_db
class TestCSPHeaders(TestCase):
    def test_report_only_header_present(self):
        response = Client().get("/")
        self.assertIn("Content-Security-Policy-Report-Only", response.headers)

    def test_report_only_default_src_self(self):
        response = Client().get("/")
        header = response.headers.get("Content-Security-Policy-Report-Only", "")
        self.assertIn("default-src 'self'", header)

    def test_report_only_no_unsafe_scripts(self):
        response = Client().get("/")
        header = response.headers.get("Content-Security-Policy-Report-Only", "")
        self.assertIn("script-src 'self'", header)
        self.assertNotIn("'unsafe-inline'", header.split("script-src")[1].split(";")[0])
