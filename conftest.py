from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User


@pytest.fixture
def user_profile(db):
    """Create a User + Profile pair, mocking image processing in Profile.save()."""
    from ahc.apps.users.models import Profile

    user = User.objects.create_user(username="testuser", password="testpass123")
    with patch("ahc.apps.users.models.Image.open") as mock_open:
        mock_img = MagicMock()
        mock_img.height = 100
        mock_img.width = 100
        mock_open.return_value = mock_img
        profile = Profile.objects.create(user=user)
    return user, profile


@pytest.fixture
def second_user_profile(db):
    """A second User + Profile for multi-user permission tests."""
    from ahc.apps.users.models import Profile

    user = User.objects.create_user(username="otheruser", password="testpass123")
    with patch("ahc.apps.users.models.Image.open") as mock_open:
        mock_img = MagicMock()
        mock_img.height = 100
        mock_img.width = 100
        mock_open.return_value = mock_img
        profile = Profile.objects.create(user=user)
    return user, profile
