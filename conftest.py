from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image as PILImage

from ahc.apps.users.models import Profile


def _create_user_profile(username):
    """Create a User + Profile pair, mocking image processing in Profile.save()."""
    mock_img = MagicMock()
    mock_img.height = 100
    mock_img.width = 100
    with patch("ahc.apps.users.models.Image.open", return_value=mock_img):
        user = User.objects.create_user(username=username, password="testpass123")  # nosec B106
    return user, Profile.objects.get(user=user)


@pytest.fixture
def user_profile(db):
    return _create_user_profile("testuser")


@pytest.fixture
def second_user_profile(db):
    """A second User + Profile for multi-user permission tests."""
    return _create_user_profile("otheruser")


@pytest.fixture
def logged_in_client(db):
    """Factory returning a fresh Client force-logged-in as the given user."""

    def make(user):
        client = Client()
        client.force_login(user)
        return client

    return make


@pytest.fixture
def png_upload():
    """Factory for a real, minimal PNG upload — Django's ImageField validates actual image content."""

    def make(name="avatar.png"):
        buf = BytesIO()
        PILImage.new("RGB", (10, 10), color="blue").save(buf, format="PNG")
        buf.seek(0)
        return SimpleUploadedFile(name, buf.read(), content_type="image/png")

    return make
