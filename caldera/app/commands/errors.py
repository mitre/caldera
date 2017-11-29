class ParseError(Exception):
    pass


class NoFileError(Exception):
    pass


class NoShareError(Exception):
    pass


class AccessDeniedError(Exception):
    pass


class NoRegKeyError(Exception):
    pass


class NoServiceError(Exception):
    pass


class NoProcessError(Exception):
    pass


class FileInUseError(Exception):
    pass


class IncorrectParameterError(Exception):
    pass


class UnresponsiveServiceError(Exception):
    pass


class ServiceNotStartedError(Exception):
    pass


class ServiceAlreadyRunningError(Exception):
    pass


class CantControlServiceError(Exception):
    pass


class ParserNotImplementedError(Exception):
    pass


class NoNetworkPathError(Exception):
    pass


class PathSyntaxError(Exception):
    pass


class AccountDisabledError(Exception):
    pass


class DomainIssueError(Exception):
    pass


class AcquireLSAError(Exception):
    pass


class AVBlockError(Exception):
    pass
