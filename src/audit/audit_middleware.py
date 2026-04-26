"""
FastAPI middleware that audit-logs PHI-touching routes.
Does not capture request body values.
"""

from __future__ import annotations

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware

from src.audit.audit_logger import AuditLogger


PHI_ROUTE_PREFIXES = ("/api/v1/intake", "/api/v1/leads", "/api/v1/compliance")


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, audit_logger: AuditLogger):
        super().__init__(app)
        self.audit_logger = audit_logger

    async def dispatch(self, request, call_next: Callable):
        response = await call_next(request)
        path = request.url.path
        if path.startswith(PHI_ROUTE_PREFIXES):
            claims = getattr(request.state, "jwt_claims", {}) or {}
            self.audit_logger.log(
                user_id=str(claims.get("user_id", "unknown")),
                tenant_id=str(claims.get("tenant_id", "unknown")),
                action=request.method.upper(),
                resource_type="route",
                resource_id=path,
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown"),
            )
        return response
