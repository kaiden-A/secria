import ssl
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401  (register every model on Base.metadata)
from app.config import get_settings
from app.database import Base, get_db
from app.dependencies import get_zitadel
from app.main import app
from app.models import (
    Environment,
    Project,
    ProjectMember,
    ProjectMemberEnv,
    ProjectRole,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)
from app.services.auth_services import create_session
from app.services.zitadel import ZitadelError

settings = get_settings()
SCHEMA = f"secria_test_{uuid.uuid4().hex[:8]}"
assert settings.db_schema != SCHEMA, "refusing to run tests against the live schema"


def _connect_args() -> dict[str, object]:
    args: dict[str, object] = {"timeout": 10}
    if settings.ssl_required:
        args["ssl_context"] = ssl.create_default_context()
    return args


# schema_translate_map instead of SET search_path on purpose: session state is
# unreliable through Neon's pooler (transaction mode) and a leaked search_path
# would leave other clients pointing at this schema after it is dropped.
test_engine = create_engine(
    settings.sqlalchemy_url,
    connect_args=_connect_args(),
    execution_options={"schema_translate_map": {settings.db_schema: SCHEMA}},
)
TestingSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    with test_engine.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
        connection.commit()
    try:
        Base.metadata.create_all(test_engine)
        yield
    finally:
        with test_engine.connect() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE'))
            connection.commit()
        test_engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables(_schema: None) -> Iterator[None]:
    yield
    tables = ", ".join(f'"{SCHEMA}"."{table.name}"' for table in Base.metadata.tables.values())
    with test_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def db() -> Iterator[DbSession]:
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db: DbSession) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, follow_redirects=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _make_user(
    db: DbSession,
    *,
    name: str = "Ada",
    email: str | None = None,
    zitadel_sub: str | None = None,
) -> User:
    user = User(
        name=name,
        email=email or f"user-{uuid.uuid4().hex[:8]}@example.com",
        zitadel_sub=zitadel_sub or f"sub-{uuid.uuid4().hex[:8]}",
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def make_user():
    return _make_user


@pytest.fixture
def sign_in(db: DbSession, client: TestClient):
    def _sign_in(user: User) -> str:
        token = create_session(db, user, settings=settings)
        client.cookies.set(settings.session_cookie_name, token)
        return token

    return _sign_in


@pytest.fixture
def make_workspace(db: DbSession):
    def _make(
        owner: User,
        *,
        name: str = "Acme",
        slug: str | None = None,
        role: WorkspaceRole = WorkspaceRole.owner,
    ) -> Workspace:
        workspace = Workspace(
            name=name,
            slug=slug or f"ws-{uuid.uuid4().hex[:8]}",
            created_by=owner.id,
        )
        db.add(workspace)
        db.flush()
        db.add(WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role=role))
        db.commit()
        return workspace

    return _make


@pytest.fixture
def add_workspace_member(db: DbSession):
    def _add(workspace: Workspace, user: User, role: WorkspaceRole = WorkspaceRole.member) -> None:
        db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=role))
        db.commit()

    return _add


@pytest.fixture
def make_project(db: DbSession):
    def _make(
        workspace: Workspace,
        *,
        name: str = "API",
        slug: str | None = None,
        environments: tuple[str, ...] = ("dev", "staging", "prod"),
    ) -> tuple[Project, list[Environment]]:
        project = Project(
            workspace_id=workspace.id,
            name=name,
            slug=slug or f"project-{uuid.uuid4().hex[:8]}",
            description="",
        )
        db.add(project)
        db.flush()
        envs: list[Environment] = []
        for position, env_slug in enumerate(environments):
            environment = Environment(
                project_id=project.id,
                name=env_slug.title(),
                slug=env_slug,
                position=position,
            )
            db.add(environment)
            envs.append(environment)
        db.commit()
        return project, envs

    return _make


@pytest.fixture
def add_project_member(db: DbSession):
    def _add(
        project: Project,
        user: User,
        role: ProjectRole = ProjectRole.viewer,
        *,
        environment_ids: list[uuid.UUID] | None = None,
    ) -> None:
        db.add(ProjectMember(project_id=project.id, user_id=user.id, role=role))
        for environment_id in environment_ids or []:
            db.add(
                ProjectMemberEnv(
                    project_id=project.id,
                    user_id=user.id,
                    environment_id=environment_id,
                )
            )
        db.commit()

    return _add


class FakeZitadel:
    """Records what would have been sent to the IdP, without the network."""

    def __init__(self, claims: dict[str, Any] | None = None) -> None:
        self.claims = claims or {
            "sub": "sub-ada",
            "email": "ada@example.com",
            "email_verified": True,
            "name": "Ada Lovelace",
        }
        self.token_requests: list[dict] = []
        self.authorize_requests: list[dict] = []
        self.verify_calls: list[dict] = []
        self.bearer_calls: list[str] = []
        self.end_session_calls: list[dict] = []

    def authorize_url(
        self,
        *,
        state: str,
        nonce: str,
        code_challenge: str,
        redirect_uri: str,
        login_hint: str | None = None,
        prompt: str | None = None,
    ) -> str:
        self.authorize_requests.append(
            {
                "state": state,
                "nonce": nonce,
                "code_challenge": code_challenge,
                "redirect_uri": redirect_uri,
                "login_hint": login_hint,
                "prompt": prompt,
            }
        )
        return f"https://idp.test/authorize?state={state}"

    def exchange_code(self, *, code: str, code_verifier: str, redirect_uri: str) -> dict:
        self.token_requests.append(
            {"code": code, "code_verifier": code_verifier, "redirect_uri": redirect_uri}
        )
        return {"id_token": "fake.id.token", "access_token": "fake-access"}

    def verify_id_token(self, id_token: str, *, nonce: str) -> dict:
        self.verify_calls.append({"id_token": id_token, "nonce": nonce})
        return {**self.claims, "nonce": nonce}

    def verify_bearer(self, token: str) -> dict:
        self.bearer_calls.append(token)
        if token == "bad-token":
            raise ZitadelError("token rejected")
        return dict(self.claims)

    def end_session_url(
        self, *, id_token_hint: str | None = None, post_logout_redirect_uri: str | None = None
    ) -> str:
        self.end_session_calls.append(
            {"id_token_hint": id_token_hint, "post_logout_redirect_uri": post_logout_redirect_uri}
        )
        return "https://idp.test/end_session"


@pytest.fixture
def fake_idp() -> FakeZitadel:
    return FakeZitadel()


@pytest.fixture
def idp_client(client: TestClient, fake_idp: FakeZitadel) -> TestClient:
    app.dependency_overrides[get_zitadel] = lambda: fake_idp
    return client
