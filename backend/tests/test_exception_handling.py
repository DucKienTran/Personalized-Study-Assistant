from types import SimpleNamespace

import pytest

from app.exceptions import BadRequestError
from app.exceptions.handlers import app_exception_handler


class DummyRequest:
    def __init__(self, path: str = "/test"):
        self.method = "GET"
        self.url = SimpleNamespace(path=path)


@pytest.mark.asyncio
async def test_app_exception_handler_returns_structured_error_payload():
    response = await app_exception_handler(
        DummyRequest(), BadRequestError("Mật khẩu không hợp lệ.")
    )

    assert response.status_code == 400
    assert (
        response.body.decode()
        == '{"detail":"Mật khẩu không hợp lệ.","error_code":"bad_request","path":"/test"}'
    )
