from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User

from ahc.apps.users.models import Profile


@pytest.fixture
def user_profile(db):
    """Create a User + Profile pair, mocking image processing in Profile.save()."""
    mock_img = MagicMock()
    mock_img.height = 100
    mock_img.width = 100
    with patch("ahc.apps.users.models.Image.open", return_value=mock_img):
        user = User.objects.create_user(username="testuser", password="testpass123")  # nosec B106
    return user, Profile.objects.get(user=user)


@pytest.fixture
def second_user_profile(db):
    """A second User + Profile for multi-user permission tests."""
    mock_img = MagicMock()
    mock_img.height = 100
    mock_img.width = 100
    with patch("ahc.apps.users.models.Image.open", return_value=mock_img):
        user = User.objects.create_user(username="otheruser", password="testpass123")  # nosec B106
    return user, Profile.objects.get(user=user)
