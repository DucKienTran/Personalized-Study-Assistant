from typing import Protocol


class LLMClient(Protocol):
    """
    Interface cho mọi Large Language Model client.
    """

    async def generate(self, prompt: str) -> str:
        """
        Gửi prompt tới LLM và trả về nội dung sinh ra.

        Raises:
            LLMGenerationError:
                Khi LLM gặp lỗi hoặc không thể sinh nội dung.
        """
        ...

    async def generate_stream(self, prompt: str): ...
