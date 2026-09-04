import uuid

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.iam.models.user import User
from app.iam.repositories.user_repo import UserRepository


class AuthService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def register(self, data):
        if await self.repo.get_by_email(data.email):
            raise ValueError("Email exists")
        user = User(
            id=str(uuid.uuid4()),
            email=data.email,
            password_hash=hash_password(data.password),
            organization_id=data.organization_id,
        )
        return await self.repo.create(user)

    async def login(self, email, password):
        user = await self.repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")
        access = create_access_token({"sub": user.id})
        refresh = create_refresh_token({"sub": user.id})
        return access, refresh
