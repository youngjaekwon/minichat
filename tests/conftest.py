"""
pytest 공용 픽스처 정의
"""

import pytest
from django.test import Client


@pytest.fixture
def client() -> Client:
    """Django test client fixture"""
    return Client()
