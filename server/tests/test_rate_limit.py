from app.main import app


def test_rate_limit_returns_json_429_with_retry_after(idp_client) -> None:
    limiter = app.state.limiter
    limiter.enabled = True
    limiter.reset()
    try:
        statuses = [
            idp_client.get("/api/auth/login").status_code for _ in range(31)
        ]
    finally:
        limiter.enabled = False
        limiter.reset()

    assert statuses[:-1] == [302] * 30
    assert statuses[-1] == 429


def test_rate_limit_response_body_is_the_standard_error_shape(idp_client) -> None:
    limiter = app.state.limiter
    limiter.enabled = True
    limiter.reset()
    try:
        for _ in range(30):
            idp_client.get("/api/auth/login")
        response = idp_client.get("/api/auth/login")
    finally:
        limiter.enabled = False
        limiter.reset()

    assert response.status_code == 429
    assert response.json() == {"error": "Too many requests. Try again shortly."}
    assert response.headers["retry-after"] == "60"
    assert response.headers["content-type"].startswith("application/json")
