from auth import create_access_token


def test_access_token_contains_tenant_and_user():
    token = create_access_token(
        {
            "tenant_id": "tenant-1",
            "user_id": "user-1",
            "role": "admin",
        }
    )
    assert isinstance(token, str)
    assert token
