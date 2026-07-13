from typing import Protocol


class LLMClient(Protocol):
    """
    Interface cho mọi Large Language Model client.

    Ví dụ:
    - GeminiClient
    - OpenAIClient
    - ClaudeClient
    """

    async def generate(self, prompt: str) -> str:
        """
        Gửi prompt tới LLM và trả về nội dung sinh ra.

        Raises:
            LLMGenerationError:
                Khi LLM gặp lỗi hoặc không thể sinh nội dung.
        """
        ...
