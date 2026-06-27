import pytest

from securai.config import Settings
from securai.modules.identity.application.service import IdentityService
from securai.modules.identity.domain.entities import ApiKey, Org, Project, User
from securai.shared.errors import AuthenticationError, AuthorizationError, ConflictError


class InMemoryRepo:
    def __init__(self):
        self.items = {}


class OrgRepo(InMemoryRepo):
    async def add(self, org: Org):
        self.items[org.id] = org

    async def get(self, org_id):
        return self.items.get(org_id)


class UserRepo(InMemoryRepo):
    async def add(self, user: User):
        self.items[user.id] = user

    async def get_by_email(self, email):
        return next((u for u in self.items.values() if u.email == email), None)

    async def get(self, user_id):
        return self.items.get(user_id)


class ProjectRepo(InMemoryRepo):
    async def add(self, project: Project):
        self.items[project.id] = project

    async def get(self, project_id):
        return self.items.get(project_id)

    async def list_for_org(self, org_id):
        return [p for p in self.items.values() if p.org_id == org_id]


class ApiKeyRepo(InMemoryRepo):
    async def add(self, key: ApiKey):
        self.items[key.id] = key

    async def get_by_hash(self, key_hash):
        return next((k for k in self.items.values() if k.key_hash == key_hash), None)

    async def get(self, key_id):
        return self.items.get(key_id)

    async def list_for_project(self, project_id):
        return [k for k in self.items.values() if k.project_id == project_id]

    async def revoke(self, key_id):
        self.items[key_id].status = "revoked"

    async def touch_last_used(self, key_id):
        pass


@pytest.fixture
def service():
    return IdentityService(
        settings=Settings(jwt_secret="unit-test-secret-unit-test-secret-32ch"),
        orgs=OrgRepo(),
        users=UserRepo(),
        projects=ProjectRepo(),
        api_keys=ApiKeyRepo(),
    )


@pytest.mark.asyncio
async def test_full_provisioning_and_auth_flow(service):
    org = await service.create_org("Acme")
    user = await service.create_user(org_id=org.id, email="a@b.com", password="pw123456")
    project = await service.create_project(org_id=org.id, name="p1")
    key, full = await service.create_api_key(org_id=org.id, project_id=project.id)

    # API key auth resolves the right principal
    principal = await service.authenticate_api_key(full)
    assert principal.org_id == org.id
    assert principal.project_id == project.id
    assert principal.auth_type == "api_key"

    # JWT login + decode
    token = await service.login(email="a@b.com", password="pw123456")
    jwt_principal = await service.principal_from_jwt(token)
    assert jwt_principal.subject == user.id
    assert jwt_principal.role == "org_admin"


@pytest.mark.asyncio
async def test_duplicate_user_rejected(service):
    org = await service.create_org("Acme")
    await service.create_user(org_id=org.id, email="a@b.com", password="pw123456")
    with pytest.raises(ConflictError):
        await service.create_user(org_id=org.id, email="a@b.com", password="pw123456")


@pytest.mark.asyncio
async def test_revoked_key_auth_fails(service):
    org = await service.create_org("Acme")
    project = await service.create_project(org_id=org.id, name="p1")
    key, full = await service.create_api_key(org_id=org.id, project_id=project.id)
    await service.revoke_api_key(key_id=key.id, org_id=org.id)
    with pytest.raises(AuthenticationError):
        await service.authenticate_api_key(full)


@pytest.mark.asyncio
async def test_authorization_rules(service):
    org = await service.create_org("Acme")
    project = await service.create_project(org_id=org.id, name="p1")
    _, full = await service.create_api_key(org_id=org.id, project_id=project.id)
    principal = await service.authenticate_api_key(full)

    IdentityService.authorize(principal, "inference:write")  # ok (default scope)
    with pytest.raises(AuthorizationError):
        IdentityService.authorize(principal, "org:manage")  # key lacks this scope
