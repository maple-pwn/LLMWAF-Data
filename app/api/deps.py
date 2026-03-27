from collections.abc import Generator

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import ensure_scope


def get_db_session() -> Generator[Session, None, None]:
    yield from get_db()


def require_admin_access(
    x_admin_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    ensure_scope("admin", admin_key=x_admin_api_key, scan_key=None, authorization=authorization)


def require_scan_access(
    x_scan_api_key: str | None = Header(default=None),
    x_admin_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    ensure_scope(
        "scan",
        admin_key=x_admin_api_key,
        scan_key=x_scan_api_key,
        authorization=authorization,
    )


DbSession = Depends(get_db_session)
AdminAccess = Depends(require_admin_access)
ScanAccess = Depends(require_scan_access)
