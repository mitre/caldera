from app.api.v2.errors import DataValidationError


def _is_integer(value):
    return isinstance(value, int)


def _is_string(value):
    return isinstance(value, (str, bytes))


def check_positive_integer(value, name=None):
    if not _is_integer(value) or value < 0:
        raise DataValidationError(
            message='Value must be a positive integer',
            name=name,
            value=value,
        )


def check_not_empty_string(value, name=None):
    if not _is_string(value) or len(value) == 0:
        raise DataValidationError(
            message='Value must be a non-empty string',
            name=name,
            value=value
        )
