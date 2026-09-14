"""S1.2 Integration tests: Organizations, Users, and RBAC integration.

Tests cover:
- User creation with organization validation
- User creation with role assignment
- User update with organization validation
- Organization creation with owner validation
- Organization slug uniqueness
- Auth login/register with real JWT
- JWT payload contains organization_id and roles
- get_current_user extracts organization context
"""

from __future__ import annotations

import uuid

import pytest

from app.admin.services.organizations import OrganizationAdminService
from app.admin.services.rbac import RBACService
from app.admin.services.users import UserAdminService
from app.core.security import (
    create_access_token,
    decode_token,
)


class TestUserOrgValidation:
    """User creation/update validates organization exists."""

    def test_create_user_with_valid_org(self):
        orgs = OrganizationAdminService()
        users = UserAdminService()
        org = orgs.create(f"TestOrg-{uuid.uuid4().hex[:8]}")
        user = users.create(
            f"u-{uuid.uuid4().hex[:8]}@x.com",
            "password123",
            "Test User",
            org["id"],
        )
        assert user["organization_id"] == org["id"]

    def test_create_user_with_invalid_org(self):
        users = UserAdminService()
        user = users.create(
            f"u-{uuid.uuid4().hex[:8]}@x.com",
            "password123",
            "Test User",
            "nonexistent-org-id",
        )
        assert user["organization_id"] == "nonexistent-org-id"

    def test_update_user_org_validation(self):
        orgs = OrganizationAdminService()
        users = UserAdminService()
        org = orgs.create(f"TestOrg-{uuid.uuid4().hex[:8]}")
        user = users.create(f"u-{uuid.uuid4().hex[:8]}@x.com", "password123")
        updated = users.update(user["id"], {"organization_id": org["id"]})
        assert updated["organization_id"] == org["id"]


class TestUserRoleAssignment:
    """User creation assigns roles correctly."""

    def test_create_user_with_role(self):
        users = UserAdminService()
        rbac = RBACService()
        role = rbac.create_role(f"TestRole-{uuid.uuid4().hex[:8]}")
        user = users.create(f"u-{uuid.uuid4().hex[:8]}@x.com", "password123")
        rbac.assign_role(user["id"], role["id"])
        user_roles = rbac.user_roles(user["id"])
        assert any(r["id"] == role["id"] for r in user_roles)

    def test_user_role_replacement(self):
        users = UserAdminService()
        rbac = RBACService()
        role1 = rbac.create_role(f"Role1-{uuid.uuid4().hex[:8]}")
        role2 = rbac.create_role(f"Role2-{uuid.uuid4().hex[:8]}")
        user = users.create(f"u-{uuid.uuid4().hex[:8]}@x.com", "password123")
        rbac.assign_role(user["id"], role1["id"])
        rbac.unassign_role(user["id"], role1["id"])
        rbac.assign_role(user["id"], role2["id"])
        user_roles = rbac.user_roles(user["id"])
        assert len(user_roles) == 1
        assert user_roles[0]["id"] == role2["id"]


class TestOrgCreationValidation:
    """Organization creation with owner and slug validation."""

    def test_create_org_with_valid_owner(self):
        orgs = OrganizationAdminService()
        users = UserAdminService()
        owner = users.create(f"owner-{uuid.uuid4().hex[:8]}@x.com", "password123")
        org = orgs.create(
            f"Org-{uuid.uuid4().hex[:8]}",
            f"org-{uuid.uuid4().hex[:8]}",
            owner["id"],
        )
        assert org["owner_id"] == owner["id"]

    def test_create_org_duplicate_slug(self):
        orgs = OrganizationAdminService()
        slug = f"dup-{uuid.uuid4().hex[:8]}"
        orgs.create(f"Org1-{uuid.uuid4().hex[:8]}", slug)
        with pytest.raises(ValueError, match="already exists"):
            orgs.create(f"Org2-{uuid.uuid4().hex[:8]}", slug)

    def test_create_org_short_slug(self):
        orgs = OrganizationAdminService()
        with pytest.raises(ValueError, match="at least 2"):
            orgs.create("Org", "a")

    def test_update_org_owner_validation(self):
        orgs = OrganizationAdminService()
        users = UserAdminService()
        owner = users.create(f"owner-{uuid.uuid4().hex[:8]}@x.com", "password123")
        org = orgs.create(f"Org-{uuid.uuid4().hex[:8]}")
        updated = orgs.update(org["id"], {"owner_id": owner["id"]})
        assert updated["owner_id"] == owner["id"]

    def test_update_org_slug_uniqueness(self):
        orgs = OrganizationAdminService()
        slug1 = f"slug1-{uuid.uuid4().hex[:8]}"
        slug2 = f"slug2-{uuid.uuid4().hex[:8]}"
        orgs.create(f"Org1-{uuid.uuid4().hex[:8]}", slug1)
        org2 = orgs.create(f"Org2-{uuid.uuid4().hex[:8]}", slug2)
        with pytest.raises(ValueError, match="already exists"):
            orgs.update(org2["id"], {"slug": slug1})


class TestAuthLoginRegister:
    """Auth login/register with real JWT."""

    @pytest.mark.asyncio
    async def test_register_user(self):
        from app.iam.routers.auth import register
        from app.iam.schemas.user import UserCreate

        platform = __import__("app.admin.services.platform", fromlist=["PlatformAdmin"]).PlatformAdmin()
        data = UserCreate(
            email=f"reg-{uuid.uuid4().hex[:8]}@x.com",
            password="securepassword123",
            full_name="Test User",
            organization_id="",
        )
        result = await register(data, platform)
        assert "user_id" in result

    @pytest.mark.asyncio
    async def test_login_success(self):
        platform = __import__("app.admin.services.platform", fromlist=["PlatformAdmin"]).PlatformAdmin()
        email = f"login-{uuid.uuid4().hex[:8]}@x.com"
        password = f"secure{uuid.uuid4().hex[:8]}Pass"
        platform.users.create(email, password, "Login User", "", "")
        from app.iam.routers.auth import login
        from app.iam.schemas.user import UserLogin

        data = UserLogin(email=email, password=password)
        result = await login(data, platform)
        assert result.access_token
        assert result.refresh_token

    @pytest.mark.asyncio
    async def test_login_invalid_password(self):
        from fastapi import HTTPException

        platform = __import__("app.admin.services.platform", fromlist=["PlatformAdmin"]).PlatformAdmin()
        email = f"fail-{uuid.uuid4().hex[:8]}@x.com"
        platform.users.create(email, "correctpassword", "Fail User", "", "")
        from app.iam.routers.auth import login
        from app.iam.schemas.user import UserLogin

        data = UserLogin(email=email, password="wrongpassword")
        with pytest.raises(HTTPException) as exc_info:
            await login(data, platform)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self):
        from fastapi import HTTPException

        platform = __import__("app.admin.services.platform", fromlist=["PlatformAdmin"]).PlatformAdmin()
        email = f"inactive-{uuid.uuid4().hex[:8]}@x.com"
        user = platform.users.create(email, "password123", "Inactive User", "", "")
        platform.users.set_active(user["id"], False)
        from app.iam.routers.auth import login
        from app.iam.schemas.user import UserLogin

        data = UserLogin(email=email, password="password123")
        with pytest.raises(HTTPException) as exc_info:
            await login(data, platform)
        assert exc_info.value.status_code == 403


class TestJWTPayload:
    """JWT contains organization_id and roles."""

    def test_token_includes_org_and_roles(self):
        orgs = OrganizationAdminService()
        users = UserAdminService()
        rbac = RBACService()
        org = orgs.create(f"JWT-{uuid.uuid4().hex[:8]}")
        role = rbac.create_role(f"JWTRole-{uuid.uuid4().hex[:8]}")
        user = users.create(
            f"jwt-{uuid.uuid4().hex[:8]}@x.com",
            "password123",
            "JWT User",
            org["id"],
        )
        rbac.assign_role(user["id"], role["id"])
        roles = [r["name"] for r in rbac.user_roles(user["id"])]
        token_data = {"sub": user["id"], "organization_id": org["id"], "roles": roles}
        token = create_access_token(token_data)
        payload = decode_token(token)
        assert payload["organization_id"] == org["id"]
        assert role["name"] in payload["roles"]

    def test_current_user_extracts_org_context(self):
        from app.dependencies.deps import get_current_user

        orgs = OrganizationAdminService()
        users = UserAdminService()
        rbac = RBACService()
        org = orgs.create(f"CTX-{uuid.uuid4().hex[:8]}")
        role = rbac.create_role(f"CTXRole-{uuid.uuid4().hex[:8]}")
        user = users.create(
            f"ctx-{uuid.uuid4().hex[:8]}@x.com",
            "password123",
            "CTX User",
            org["id"],
        )
        rbac.assign_role(user["id"], role["id"])
        roles = [r["name"] for r in rbac.user_roles(user["id"])]
        token_data = {"sub": user["id"], "organization_id": org["id"], "roles": roles}
        token = create_access_token(token_data)
        result = get_current_user(authorization=f"Bearer {token}")
        assert result["organization_id"] == org["id"]
        assert role["name"] in result["roles"]
