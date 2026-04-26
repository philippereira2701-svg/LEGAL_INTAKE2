"""
Tenant isolation dependency for FastAPI routes.
Ensures JWT tenant claim matches requested resource tenant.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status


def tenant_guard(request: Request) -> str:
    claims = getattr(request.state, "jwt_claims", None)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth claims")

    jwt_tenant_id = str(claims.get("tenant_id", ""))
    target_tenant_id = (
        request.path_params.get("tenant_id")
        or request.query_params.get("tenant_id")
        or request.headers.get("x-tenant-id", "")
    )
    if target_tenant_id and jwt_tenant_id != str(target_tenant_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant isolation violation")
    return jwt_tenant_id


TenantGuard = Depends(tenant_guard)
