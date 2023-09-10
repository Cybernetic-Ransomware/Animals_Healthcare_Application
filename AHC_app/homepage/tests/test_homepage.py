from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from homepage.models import AnimalTitle

client = Client()


class TestHomepage(TestCase):
    def setUp(self) -> None:
        my_user = User.objects.create(username='test_user_placeholder')
        self.my_animal_title = AnimalTitle.objects.create(title='test_animal_placeholder', owner=my_user)

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
        resp = client.get('/')
        actual_status_code = resp.status_code

        # assert actual_status_code == expected_status_code
        self.assertEquals(expected_status_code, actual_status_code)

    def test_should_return_valid_render_template_name_when_view_is_get_called(self):
        expected_template_name = 'homepage/homepage.html'
        resp = client.get('/')

        self.assertTemplateUsed(resp, expected_template_name)
