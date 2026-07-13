from app.exceptions import InternalServerError


class AIConfigurationError(InternalServerError):
    error_code = "ai_configuration_error"

    def __init__(
        self, message: str = "Cấu hình AI chưa hợp lệ. Vui lòng kiểm tra lại hệ thống."
    ):
        super().__init__(message)


class LLMGenerationError(InternalServerError):
    error_code = "llm_generation_failed"

    def __init__(self, message: str = "Không thể sinh nội dung từ AI."):
        super().__init__(message)


class EmptyLLMResponseError(InternalServerError):
    error_code = "llm_empty_response"

    def __init__(self, message: str = "AI không trả về nội dung hợp lệ."):
        super().__init__(message)
