import secrets

from core.config import get_settings
from core.errors import AppError


def ensure_scope(
    scope: str,
    admin_key: str | None,
    scan_key: str | None,
    authorization: str | None,
) -> None:
    settings = get_settings()
    if settings.testing:
        return
    if authorization:
        raise AppError(401, "Bearer authentication is not enabled for this deployment.")
    if scope == "admin":
        if admin_key and secrets.compare_digest(admin_key, settings.admin_api_key):
            return
        raise AppError(401, "Missing or invalid admin credentials.")
    if admin_key and secrets.compare_digest(admin_key, settings.admin_api_key):
        return
    if scan_key and secrets.compare_digest(scan_key, settings.scan_api_key):
        return
    raise AppError(401, "Missing or invalid scan credentials.")
