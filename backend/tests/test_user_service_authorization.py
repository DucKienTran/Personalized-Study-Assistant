from app.exceptions import ForbiddenError
import pytest

from app.schemas.user_schema import CurrentUser
from app.services.user_service import UserService


class DummyDB:
    def query(self, *_args, **_kwargs):
        raise AssertionError("Not used in this test")


class DummyRedis:
    pass


class DummyPresence:
    pass


def test_get_all_users_rejects_non_admin():
    service = UserService(DummyDB(), DummyRedis(), DummyPresence())
    current_user = CurrentUser(
        id=1, email="user@example.com", role="client", permissions=[]
    )

    with pytest.raises(ForbiddenError) as exc_info:
        service.get_all_users(current_user)

    assert exc_info.value.status_code == 403
