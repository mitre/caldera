import pytest

from app.api.v2 import errors
from app.api.v2 import validation


def test_check_positive_integer_throws_on_non_int():
    with pytest.raises(errors.DataValidationError):
        validation.check_positive_integer(None)


def test_check_positive_integer_throws_on_negative_int():
    with pytest.raises(errors.DataValidationError):
        validation.check_positive_integer(-1)


def test_check_positive_integer_passes_on_zero():
    thrown = None

    try:
        validation.check_positive_integer(0)
    except Exception as ex:
        thrown = ex
    assert thrown is None


def test_check_positive_integer_passes_on_positive_int():
    thrown = None

    try:
        validation.check_positive_integer(100)
    except Exception as ex:
        thrown = ex
    assert thrown is None


def test_check_not_empty_string_throws_on_non_string():
    with pytest.raises(errors.DataValidationError):
        validation.check_not_empty_string(None)


def test_check_not_empty_string_throws_on_empty_string():
    with pytest.raises(errors.DataValidationError):
        validation.check_not_empty_string('')


def test_check_not_empty_string_passes_on_non_empty_string():
    thrown = None

    try:
        validation.check_not_empty_string('foobar')
    except Exception as ex:
        thrown = ex
    assert thrown is None
