class CliError(Exception):
    exit_code = 1


class AuthError(CliError):
    exit_code = 2


class PermissionDenied(CliError):
    exit_code = 3


class ConflictError(CliError):
    exit_code = 4


class ApiError(CliError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.exit_code = {401: 2, 403: 3, 409: 4}.get(status, 1)
