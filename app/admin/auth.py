# app/admin/auth.py
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from app.config import settings


class AdminAuth(AuthenticationBackend):
    async def authenticate(self, request: Request) -> bool:
        """Called by SQLAdmin on each /admin/* request. Return False → redirect to /admin/login."""
        return request.session.get("token") == "authenticated"

    async def login(self, request: Request) -> bool:
        form = await request.form()
        if (form.get("username") == settings.admin_user
                and form.get("password") == settings.admin_pass):
            request.session["token"] = "authenticated"
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True
