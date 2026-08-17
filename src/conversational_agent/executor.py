from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import httpx

from .config import get_settings
from .digest import DigestStore
from .models import ApiResult, PendingCall
from .validation import OperationValidator


class DeterministicRestExecutor:
    """
    Executes only allowlisted operations from the digest.

    The LLM never supplies a URL or HTTP method. Both come from the digest.
    """

    def __init__(self, digest: DigestStore, validator: OperationValidator):
        self.digest = digest
        self.validator = validator
        self.settings = get_settings()

    async def execute(self, call: PendingCall) -> ApiResult:
        operation = self.digest.get_operation(call.operation_id)
        if operation is None:
            return ApiResult(
                operation_id=call.operation_id,
                ok=False,
                method="BLOCKED",
                path="",
                error={"code": "UNKNOWN_OPERATION", "message": "Operation is not defined in the service digest."},
            )

        validation_errors = self.validator.validate_call(call)
        if validation_errors:
            return ApiResult(
                operation_id=call.operation_id,
                ok=False,
                method=operation["http"]["method"],
                path=operation["http"]["path"],
                request={
                    "path_params": call.path_params,
                    "query_params": call.query_params,
                    "body": call.body,
                },
                error={"code": "AGENT_REQUEST_VALIDATION_FAILED", "details": validation_errors},
            )

        method = operation["http"]["method"].upper()
        template = operation["http"]["path"]
        path = template
        for name, value in call.path_params.items():
            path = path.replace("{" + name + "}", quote(str(value), safe=""))

        if "{" in path or "}" in path:
            return ApiResult(
                operation_id=call.operation_id,
                ok=False,
                method=method,
                path=template,
                error={"code": "UNRESOLVED_PATH_PARAMETER", "message": f"Could not resolve path template {template}"},
            )

        base = self.settings.order_service_base_url.rstrip("/")
        url = f"{base}{path}"

        request_summary = {
            "path_params": call.path_params,
            "query_params": {k: v for k, v in call.query_params.items() if v is not None},
            "body": call.body,
        }

        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.request(
                    method,
                    url,
                    params=request_summary["query_params"] or None,
                    json=call.body if call.body is not None else None,
                    headers={"Accept": "application/json"},
                )
        except httpx.HTTPError as exc:
            return ApiResult(
                operation_id=call.operation_id,
                ok=False,
                method=method,
                path=path,
                request=request_summary,
                error={"code": "SERVICE_CONNECTION_ERROR", "message": str(exc)},
            )

        try:
            data: Any = response.json()
        except (json.JSONDecodeError, ValueError):
            data = response.text

        warnings = self.validator.validate_response(call.operation_id, response.status_code, data)
        if 200 <= response.status_code < 300:
            return ApiResult(
                operation_id=call.operation_id,
                ok=True,
                status_code=response.status_code,
                method=method,
                path=path,
                request=request_summary,
                data=data,
                response_validation_warnings=warnings,
            )

        return ApiResult(
            operation_id=call.operation_id,
            ok=False,
            status_code=response.status_code,
            method=method,
            path=path,
            request=request_summary,
            error=data,
            response_validation_warnings=warnings,
        )
