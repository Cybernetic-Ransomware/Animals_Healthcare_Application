from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from PIL import Image as PILImage

from ahc.apps.users.models import Profile

_DB_FIXTURES = frozenset({"db", "transactional_db", "client", "admin_client", "django_user_model", "live_server"})


def pytest_collection_modifyitems(items):
    """Fail collection on a missing or inconsistent category marker — CI selects jobs by marker."""
    errors = []
    for item in items:
        is_unit = item.get_closest_marker("unit") is not None
        is_integration = item.get_closest_marker("integration") is not None
        if is_unit == is_integration:
            errors.append(f"{item.nodeid}: needs exactly one of 'unit' or 'integration'")
        elif is_unit and (item.get_closest_marker("django_db") or _DB_FIXTURES & set(item.fixturenames)):
            errors.append(f"{item.nodeid}: 'unit' test uses the database or the Django test client")
    if errors:
        raise pytest.UsageError("Invalid test category markers:\n" + "\n".join(errors))


@pytest.fixture(scope="session", autouse=True)
def fast_password_hasher():
    """PBKDF2 dominates fixture setup; no test depends on the hashing algorithm."""
    with override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]):
        yield


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
