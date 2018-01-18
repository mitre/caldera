class ParseError(Exception):
    """Represent a generic parsing error"""
    pass


class NoFileError(Exception):
    """Represents an error caused by a file not being found"""
    pass


class NoShareError(Exception):
    """Represents an error caused by a share not existing"""
    pass


class AccessDeniedError(Exception):
    """Represents an error caused because access was denied"""
    pass


class NoRegKeyError(Exception):
    """Represents an error caused because a registry key was missing"""
    pass


class NoServiceError(Exception):
    """Represents an error caused because a service does not exist"""
    pass


class NoProcessError(Exception):
    """Represents an error caused because a process does not exist"""
    pass


class FileInUseError(Exception):
    """Represents an error caused because a file is currently in use"""
    pass


class IncorrectParameterError(Exception):
    """Represents an error caused because a parameter was incorrect"""
    pass


class UnresponsiveServiceError(Exception):
    """Represents an error caused because a service is unresponsive"""
    pass


class ServiceNotStartedError(Exception):
    """Represents an error caused because a service is not started"""
    pass


class ServiceAlreadyRunningError(Exception):
    """Represents an error caused because a service is already running"""
    pass


class CantControlServiceError(Exception):
    """Represents an error caused because a service cannot be controlled"""
    pass


class ParserNotImplementedError(Exception):
    """Represents an error caused because the parser does support it"""
    pass


class NoNetworkPathError(Exception):
    """Represents an error caused because a network path does not exist"""
    pass


class PathSyntaxError(Exception):
    """Represents an error caused because the syntax of a path is incorrect"""
    pass


class AccountDisabledError(Exception):
    """Represents an error caused because an account is disabled"""
    pass


class DomainIssueError(Exception):
    """Represents an error caused because there is a domain issue"""
    pass


class AcquireLSAError(Exception):
    """Represents an error caused because the process could not acquire access to LSA"""
    pass


class AVBlockError(Exception):
    """Represents an error caused because AntiVirus software blocked the action"""
    pass
