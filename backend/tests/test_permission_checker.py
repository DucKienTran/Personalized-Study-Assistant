from fastapi import HTTPException
import pytest

from app.api.dependencies import PermissionChecker
from app.schemas.user_schema import CurrentUser


def test_permission_checker_allows_matching_permission():
    current_user = CurrentUser(
        id=1,
        email="user@example.com",
        role="client",
        permissions=["document:create"],
    )

    checker = PermissionChecker("document:create")

    result = checker(current_user)

    assert result is current_user


def test_permission_checker_rejects_missing_permission():
    current_user = CurrentUser(
        id=1,
        email="user@example.com",
        role="client",
        permissions=["read"],
    )

    checker = PermissionChecker("document:create")

    with pytest.raises(HTTPException) as exc_info:
        checker(current_user)

    assert exc_info.value.status_code == 403
