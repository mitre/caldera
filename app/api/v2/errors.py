class DataValidationError(Exception):
    def __init__(self, message=None, name=None, value=None):
        super().__init__(message or 'Data validation error occurred')
        self.name = name
        self.value = value


class RequestBodyParseError(Exception):
    """Base class for HTTP body parsing errors."""
    pass


class RequestValidationError(RequestBodyParseError):
    """Raised when an http request body contains json that is not schema-valid."""

    def __init__(self, message=None, errors=None):
        super().__init__(message or 'Schema validation error occurred while parsing json body')
        self.errors = errors


class RequestUnparsableJsonError(RequestBodyParseError):
    """Raised when a request body is not parsable (i.e., it is not well-formed json)"""

    def __init__(self, message=None):
        super().__init__(message or 'Request json could not be parsed')
