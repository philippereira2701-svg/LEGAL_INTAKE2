"""
Response sanitizer middleware.
Scans JSON responses for potential PII patterns and emits audit warnings on detection.
"""

from __future__ import annotations

import json
import re
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware


class ResponseSanitizerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, audit_logger):
        super().__init__(app)
        self.audit_logger = audit_logger

    async def dispatch(self, request, call_next: Callable):
        response = await call_next(request)

        if "application/json" not in (response.headers.get("content-type") or ""):
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        text = body.decode("utf-8", errors="ignore")
        patterns = [
            r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
            r"(?:\+?1[\s\-\.]?)?(?:\(?\d{3}\)?[\s\-\.]?)\d{3}[\s\-\.]?\d{4}",
            r"\b\d{3}-\d{2}-\d{4}\b",
            r"\b(19|20)\d{2}-\d{2}-\d{2}\b",
        ]
        if any(re.search(p, text) for p in patterns):
            claims = getattr(request.state, "jwt_claims", {}) or {}
            self.audit_logger.log(
                user_id=str(claims.get("user_id", "unknown")),
                tenant_id=str(claims.get("tenant_id", "unknown")),
                action="PII_LEAK_WARNING",
                resource_type="response",
                resource_id=request.url.path,
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown"),
            )

        from starlette.responses import Response

        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
