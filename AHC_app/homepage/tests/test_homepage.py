from html.parser import HTMLParser

from django.contrib.auth.models import User
from django.test import Client, TestCase
from homepage.models import AnimalTitle

client = Client()


class HrefParser(HTMLParser):
    found_href = False

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for attr, value in attrs:
                if attr == "href" and value == "#":
                    self.found_href = True


class TestHomepage(TestCase):
    def setUp(self) -> None:
        my_user = User.objects.create(username="test_user_placeholder")
        self.my_animal_title = AnimalTitle.objects.create(title="test_animal_placeholder", owner=my_user)

    def tearDown(self) -> None:
        pass

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_should_return_status_code_200_when_view_is_get_called(self):
        expected_status_code = 200
        resp = client.get("/")
        actual_status_code = resp.status_code

        # assert actual_status_code == expected_status_code
        self.assertEquals(expected_status_code, actual_status_code)

    def test_should_return_valid_render_template_name_when_view_is_get_called(self):
        expected_template_name = "homepage/homepage.html"
        resp = client.get("/")

        self.assertTemplateUsed(resp, expected_template_name)


class TestHomepageWithNoHashHref(TestHomepage):
    def test_no_hash_href(self):
        url = "/"
        resp = client.get(url, follow=True)
        html = resp.content.decode("utf-8")

        parser = HrefParser()
        parser.feed(html)

        assert not parser.found_href, f"Found an href with value '#' in {url}"
