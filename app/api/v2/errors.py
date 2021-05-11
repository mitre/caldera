class DataValidationError(Exception):
    def __init__(self, message=None, name=None, value=None):
        super().__init__(message or 'Data validation error occurred')
        self.name = name
        self.value = value


class RequestBodyParseError(Exception):
    pass


class RequestValidationError(RequestBodyParseError):
    def __init__(self, message=None, errors=None):
        super().__init__(message or 'Request is not schema-valid')
        self.errors = errors


class RequestUnparsableJsonError(RequestBodyParseError):
    def __init__(self, message=None):
        super().__init__(message or 'Request has unparsable json')
