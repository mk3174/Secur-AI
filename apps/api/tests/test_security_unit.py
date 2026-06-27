from securai.shared.security import (
    create_access_token,
    decode_access_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)


def test_api_key_generation_and_hash():
    full, prefix, h = generate_api_key("sk_securai")
    assert full.startswith("sk_securai_")
    assert prefix.startswith("sk_securai_")
    assert len(prefix) == len("sk_securai") + 9
    assert h == hash_api_key(full)
    # hash is deterministic and != raw key
    assert h != full
    assert hash_api_key(full) == hash_api_key(full)


def test_password_hashing_roundtrip():
    h = hash_password("s3cret!")
    assert verify_password("s3cret!", h) is True
    assert verify_password("wrong", h) is False


def test_jwt_roundtrip():
    secret = "a-sufficiently-long-test-secret-key-0123456789"
    token = create_access_token(
        subject="user-1",
        secret=secret,
        algorithm="HS256",
        ttl_seconds=60,
        claims={"org_id": "o1", "role": "org_admin"},
    )
    payload = decode_access_token(token, secret=secret, algorithm="HS256")
    assert payload["sub"] == "user-1"
    assert payload["org_id"] == "o1"
    assert payload["role"] == "org_admin"
