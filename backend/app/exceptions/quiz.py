from app.exceptions.base import BadRequestError, NotFoundError


class QuizNotFoundError(NotFoundError):
    error_code = "quiz_not_found"

    def __init__(
        self,
        message: str = "Không tìm thấy đề thi phù hợp hoặc bạn không có quyền truy cập.",
    ):
        super().__init__(message)


class InvalidQuizOperationError(BadRequestError):
    error_code = "invalid_quiz_operation"

    def __init__(self, message: str = "Hành động không hợp lệ với chế độ của đề thi."):
        super().__init__(message)
