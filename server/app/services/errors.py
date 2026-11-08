"""Small domain exceptions that routers translate.

Services raise these instead of HTTPException so they stay framework-free;
main.py maps them to the {"error": "..."} shape.
"""


class ServiceError(Exception):
    status_code = 400
    default_message = "Something went wrong."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class UnauthorizedError(ServiceError):
    status_code = 401
    default_message = "Not signed in."


class NotFoundError(ServiceError):
    status_code = 404
    default_message = "Not found."


class ForbiddenError(ServiceError):
    status_code = 403
    default_message = "Not allowed."


class ConflictError(ServiceError):
    status_code = 409
    default_message = "That already exists."


class InvalidError(ServiceError):
    status_code = 422
    default_message = "Check the details you sent."


class UpstreamError(ServiceError):
    status_code = 502
    default_message = "The identity provider is unavailable."


class UnavailableError(ServiceError):
    status_code = 503
    default_message = "That is not configured yet."
