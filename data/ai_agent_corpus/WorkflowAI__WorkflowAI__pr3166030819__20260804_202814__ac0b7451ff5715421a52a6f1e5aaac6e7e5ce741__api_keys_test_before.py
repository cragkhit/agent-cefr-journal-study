from datetime import datetime
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from core.domain.api_key import APIKey
from core.domain.users import UserIdentifier


@pytest.fixture(scope="function")
def mock_api_keys_service(test_app: FastAPI) -> Mock:
    from api.dependencies.services import APIKeyService, api_key_service

    mock = Mock(spec=APIKeyService)
    test_app.dependency_overrides[api_key_service] = lambda: mock
    return mock


class TestNoAnonymousOrganization:
    async def test_create_api_key(
        self,
        test_api_client: AsyncClient,
        mock_user_org_dep: Mock,
        mock_api_keys_service: Mock,
    ):
        # Anonymous organization
        mock_user_org_dep.return_value.org_id = None
        mock_user_org_dep.return_value.owner_id = None
        assert mock_user_org_dep.return_value.is_anonymous is True, "Organization should be anonymous"

        response = await test_api_client.post("/_/api/keys")
        assert response.status_code == 401
        assert response.json() == {"detail": "Endpoint is only available for non-anonymous tenants"}
        mock_api_keys_service.create_key.assert_not_called()

        # Non-anonymous organization as a sanity check
        mock_user_org_dep.return_value.org_id = "org_123"
        assert mock_user_org_dep.return_value.is_anonymous is False, "Organization should not be anonymous"

        mock_api_keys_service.create_key.return_value = (
            APIKey(
                id="1",
                name="test",
                partial_key="123",
                created_at=datetime.now(),
                last_used_at=None,
                created_by=UserIdentifier(),
            ),
            "hello",
        )

        response = await test_api_client.post("/_/api/keys", json={"name": "test"})
        assert response.status_code == 201
        mock_api_keys_service.create_key.assert_awaited_once()
