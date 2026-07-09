from app.exceptions.base import UnauthorizedError, ForbiddenError


class InvalidTokenError(UnauthorizedError):
    error_code = "invalid_token"

    def __init__(self):
        super().__init__("Token không hợp lệ hoặc đã bị thay đổi.")


class ExpiredTokenError(UnauthorizedError):
    error_code = "token_expired"

    def __init__(self):
        super().__init__("Token đã hết hạn sử dụng.")


class InvalidTokenTypeError(UnauthorizedError):
    error_code = "invalid_token_type"

    def __init__(self, expected_type: str):
        super().__init__(
            f"Loại token không hợp lệ. Yêu cầu: {expected_type} token"
        )


class MissingUserIdentityError(UnauthorizedError):
    error_code = "missing_user_identity"

    def __init__(self):
        super().__init__(
            "Token không hợp lệ: Thiếu thông tin định danh người dùng."
        )


class PermissionDeniedError(ForbiddenError):
    error_code = "permission_denied"

    def __init__(self, permission: str):
        super().__init__(
            f"Bạn không có quyền thực hiện hành động này. Yêu cầu quyền: '{permission}'"
        )


class InvalidAdminRegistrationKeyError(ForbiddenError):
    error_code = "invalid_admin_registration_key"

    def __init__(self):
        super().__init__("Mã xác thực Admin không hợp lệ.")