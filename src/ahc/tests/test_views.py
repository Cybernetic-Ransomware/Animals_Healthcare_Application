from unittest.mock import patch

import pytest
from django.db import DatabaseError


@pytest.mark.unit
def test_livez_returns_ok_without_touching_the_database(client):
    response = client.get("/livez")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.unit
@pytest.mark.django_db
def test_readyz_returns_ok_when_database_is_reachable(client):
    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.unit
def test_readyz_returns_503_when_database_is_down(client):
    with patch("ahc.views.connection") as mock_connection:
        mock_connection.cursor.side_effect = DatabaseError("connection refused")
        response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
