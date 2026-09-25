from html.parser import HTMLParser
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from pytest_django.asserts import assertTemplateUsed

from ahc.apps.homepage.models import AnimalTitle


class HrefParser(HTMLParser):
    found_href = False

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for attr, value in attrs:
                if attr == "href" and value == "#":
                    self.found_href = True


@pytest.fixture
def animal_title():
    mock_img = MagicMock()
    mock_img.height = 100
    mock_img.width = 100
    with patch("ahc.apps.users.models.Image.open", return_value=mock_img):
        my_user = User.objects.create(username="test_user_placeholder")
    return AnimalTitle.objects.create(title="test_animal_placeholder", owner=my_user)


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.usefixtures("animal_title")
class TestHomepage:
    def test_should_return_status_code_200_when_view_is_get_called(self, client):
        expected_status_code = 200
        resp = client.get("/")
        actual_status_code = resp.status_code

        assert actual_status_code == expected_status_code

    def test_should_return_valid_render_template_name_when_view_is_get_called(self, client):
        expected_template_name = "homepage/homepage.html"
        resp = client.get("/")

        assertTemplateUsed(resp, expected_template_name)


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.usefixtures("animal_title")
class TestHomepageWithNoHashHref:
    def test_no_hash_href(self, client):
        url = "/"
        resp = client.get(url, follow=True)
        html = resp.content.decode("utf-8")

        parser = HrefParser()
        parser.feed(html)

        assert not parser.found_href, f"Found an href with value '#' in {url}"
