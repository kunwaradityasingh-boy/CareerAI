from backend.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


def test_password_hashing():
    password = "CareerAI_Test_2026!"

    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword123!", hashed)


def test_jwt_creation_and_decoding():
    token = create_access_token(123)

    payload = decode_access_token(token)

    assert payload["sub"] == "123"
    assert "exp" in payload
    assert "iat" in payload
