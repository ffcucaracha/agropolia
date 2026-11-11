import pytest

from agropolia.security import normalize_email, normalize_phone, validate_inn


def test_normalize_email():
    assert normalize_email(" User@Example.RU ") == "user@example.ru"


def test_invalid_email_rejected():
    with pytest.raises(ValueError):
        normalize_email("not-an-email")


def test_normalize_russian_phone():
    assert normalize_phone("8 (900) 123-45-67") == "+79001234567"
    assert normalize_phone("9001234567") == "+79001234567"


def test_validate_inn_10_digits():
    assert validate_inn("7707083893") == "7707083893"


def test_invalid_inn_rejected():
    with pytest.raises(ValueError):
        validate_inn("7707083894")
