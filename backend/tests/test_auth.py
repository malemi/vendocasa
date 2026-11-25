"""Token verification (backend/app/auth.py): every way a token can be wrong."""

from __future__ import annotations

import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app import auth
from app.auth import Account, AuthFailure, verify_token
from app.config import settings
from app.services import disposable_domains
from tests.auth_helpers import OWNER_ID, make_token


async def _failure_code(token: str) -> tuple[str, int]:
    with pytest.raises(AuthFailure) as info:
        await verify_token(token)
    return info.value.code, info.value.status_code


@pytest.mark.asyncio
async def test_valid_token_yields_its_account():
    account = await verify_token(make_token("aaaa1111-0000-4000-8000-000000000001", "Mario@Example.com"))
    assert account == Account(id="aaaa1111-0000-4000-8000-000000000001", email="mario@example.com")
    assert not account.is_owner


@pytest.mark.asyncio
async def test_owner_is_the_configured_subject_only():
    assert (await verify_token(make_token(OWNER_ID))).is_owner
    # The owner's email under another subject is not the owner.
    assert not (await verify_token(make_token(email="owner@example.com"))).is_owner


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"exp": int(time.time()) - 10}, ("session_expired", 401)),
        ({"aud": "anon"}, ("invalid_token", 401)),
        ({"iss": "https://other-project.supabase.co/auth/v1"}, ("invalid_token", 401)),
        ({"is_anonymous": True}, ("invalid_token", 401)),
        ({"role": "anon"}, ("invalid_token", 401)),
        ({"email": ""}, ("invalid_token", 401)),
        ({"email": "someone@mailinator.com"}, ("disposable_email", 403)),
        ({"email": "someone@inbox.yopmail.com"}, ("disposable_email", 403)),
    ],
)
async def test_wrong_claims_are_refused(overrides, expected):
    assert await _failure_code(make_token(**overrides)) == expected


@pytest.mark.asyncio
async def test_wrong_signature_and_garbage_are_refused():
    forged = jwt.encode(
        {"sub": "x", "email": "a@example.com", "aud": "authenticated", "iss": auth.token_issuer(),
         "role": "authenticated", "exp": int(time.time()) + 60},
        "a-different-secret-entirely-0123456789",
        algorithm="HS256",
    )
    assert await _failure_code(forged) == ("invalid_token", 401)
    assert await _failure_code("not-a-jwt") == ("invalid_token", 401)


@pytest.mark.asyncio
async def test_missing_identity_configuration_refuses_with_503(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "")
    assert await _failure_code(make_token()) == ("auth_unavailable", 503)


@pytest.mark.asyncio
async def test_unavailable_domain_list_fails_closed(monkeypatch):
    async def _broken(email):
        raise RuntimeError("database down")

    monkeypatch.setattr(auth, "is_disposable", _broken)
    assert await _failure_code(make_token()) == ("auth_unavailable", 503)


def test_domain_candidates_cover_parent_domains():
    assert disposable_domains.email_domain_candidates("a@Mail.Tempmail.Example.") == [
        "mail.tempmail.example",
        "tempmail.example",
        "example",
    ]


class _JwksServer:
    """An httpx transport serving one JWKS document and counting fetches."""

    def __init__(self, jwks: dict):
        self.jwks = jwks
        self.fetches = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/v1/.well-known/jwks.json"
        self.fetches += 1
        return httpx.Response(200, json=self.jwks)


@pytest.fixture
def es256(monkeypatch):
    """Switch verification to ES256 against a local JWKS of one EC key."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_jwk = jwt.algorithms.ECAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    public_jwk.update({"kid": "key-1", "alg": "ES256", "use": "sig"})
    server = _JwksServer({"keys": [public_jwk]})

    real_client = httpx.AsyncClient

    def _client(**kwargs):
        return real_client(transport=httpx.MockTransport(server.handler), **kwargs)

    monkeypatch.setattr(auth.httpx, "AsyncClient", _client)
    monkeypatch.setattr(settings, "supabase_jwt_algorithm", "ES256")
    auth.jwks_cache.clear()
    yield private_key, server
    auth.jwks_cache.clear()


def _es256_token(private_key, kid: str = "key-1", **overrides) -> str:
    now = int(time.time())
    claims = {"sub": "bbbb2222-0000-4000-8000-000000000002", "email": "luisa@example.com",
              "aud": "authenticated", "iss": auth.token_issuer(), "role": "authenticated",
              "is_anonymous": False, "iat": now, "exp": now + 3600}
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="ES256", headers={"kid": kid})


@pytest.mark.asyncio
async def test_es256_token_verifies_against_jwks(es256):
    private_key, server = es256
    account = await verify_token(_es256_token(private_key))
    assert account.email == "luisa@example.com"
    await verify_token(_es256_token(private_key))
    assert server.fetches == 1  # the key is cached


@pytest.mark.asyncio
async def test_unknown_key_id_refetches_at_most_once_a_minute(es256):
    private_key, server = es256
    await verify_token(_es256_token(private_key))
    assert server.fetches == 1
    # An unknown key ID right after a fetch is refused without another fetch.
    assert await _failure_code(_es256_token(private_key, kid="key-unknown")) == ("invalid_token", 401)
    assert await _failure_code(_es256_token(private_key, kid="key-unknown")) == ("invalid_token", 401)
    assert server.fetches == 1


@pytest.mark.asyncio
async def test_algorithm_comes_from_configuration_not_the_token(es256):
    # An HS256 token naming a real key ID is refused while ES256 is
    # configured: the token header cannot choose the algorithm.
    private_key, _server = es256
    await verify_token(_es256_token(private_key))  # caches key-1
    hs256_with_kid = jwt.encode(
        {"sub": "x", "email": "a@example.com", "aud": "authenticated", "iss": auth.token_issuer(),
         "role": "authenticated", "exp": int(time.time()) + 60},
        settings.supabase_jwt_secret,
        algorithm="HS256",
        headers={"kid": "key-1"},
    )
    assert await _failure_code(hs256_with_kid) == ("invalid_token", 401)
    assert await _failure_code(make_token()) == ("invalid_token", 401)  # no key ID at all


class _FlakyJwksServer(_JwksServer):
    """Fails the first `failures` fetches, then serves the keys."""

    def __init__(self, jwks: dict, failures: int):
        super().__init__(jwks)
        self.failures = failures

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.fetches += 1
        if self.fetches <= self.failures:
            return httpx.Response(503)
        return httpx.Response(200, json=self.jwks)


@pytest.mark.asyncio
async def test_a_failed_key_fetch_is_unavailable_never_invalid(es256, monkeypatch):
    private_key, server = es256
    flaky = _FlakyJwksServer(server.jwks, failures=1)
    original_client = httpx._client.AsyncClient  # the fixture already patched httpx.AsyncClient
    monkeypatch.setattr(auth.httpx, "AsyncClient",
                        lambda **kw: original_client(transport=httpx.MockTransport(flaky.handler), **kw))
    clock = [1000.0]
    monkeypatch.setattr(auth.time, "monotonic", lambda: clock[0])
    token = _es256_token(private_key)

    # The fetch fails: the session is not called invalid, and nothing signs the user out.
    assert await _failure_code(token) == ("auth_unavailable", 503)
    # Within the retry interval, no new fetch is made.
    clock[0] += 1
    assert await _failure_code(token) == ("auth_unavailable", 503)
    assert flaky.fetches == 1
    # After the interval the fetch succeeds and the same token is valid.
    clock[0] += auth.JWKS_RETRY_AFTER_FAILURE_SECONDS
    assert (await verify_token(token)).email == "luisa@example.com"
    assert flaky.fetches == 2
