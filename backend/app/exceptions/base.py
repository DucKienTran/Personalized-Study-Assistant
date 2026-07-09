class AppError(Exception):
    status_code: int = 500
    error_code: str = "internal_server_error"

    def __init__(self, message: str, *, details: dict | None = None):
        self.message = message
        self.details = details
        super().__init__(message)


class BadRequestError(AppError):
    status_code = 400
    error_code = "bad_request"


class UnauthorizedError(AppError):
    status_code = 401
    error_code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    error_code = "forbidden"


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"


class ConflictError(AppError):
    status_code = 409
    error_code = "conflict"


class InternalServerError(AppError):
    status_code = 500
    error_code = "internal_server_error"

    def __init__(self, message: str = "Đã xảy ra lỗi hệ thống.", *, details: dict | None = None):
        super().__init__(message, details=details)
