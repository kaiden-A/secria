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


def test_limiter_allows_endpoints_that_return_models(
    client, sign_in, make_user, make_workspace, make_project, db
) -> None:
    owner = make_user(db)
    workspace = make_workspace(owner)
    project, envs = make_project(workspace)
    sign_in(owner)
    created = client.post(
        f"/api/v1/projects/{project.id}/environments/{envs[0].id}/service-tokens",
        json={"name": "scope", "access": "read"},
    )
    assert created.status_code == 201, created.text

    limiter = app.state.limiter
    limiter.enabled = True
    limiter.reset()
    try:
        response = client.get(
            "/api/v1/service-tokens/current",
            headers={"Authorization": f"Bearer {created.json()['token']}"},
        )
    finally:
        limiter.enabled = False
        limiter.reset()

    assert response.status_code == 200, response.text
    assert response.json()["environmentSlug"] == "dev"
