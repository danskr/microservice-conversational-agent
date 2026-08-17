from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator

from .digest import DigestStore
from .models import PendingCall


class OperationValidator:
    """Validates planner output against the API contract embedded in the digest."""

    def __init__(self, digest: DigestStore):
        self.digest = digest

    def validate_call(self, call: PendingCall) -> list[str]:
        operation = self.digest.get_operation(call.operation_id)
        if operation is None:
            return [f"Unknown operation_id: {call.operation_id}"]

        errors: list[str] = []
        contract = operation.get("contract", {})
        parameters = contract.get("parameters", []) or []

        path_defs = {p["name"]: p for p in parameters if p.get("in") == "path"}
        query_defs = {p["name"]: p for p in parameters if p.get("in") == "query"}

        for name, definition in path_defs.items():
            value = call.path_params.get(name)
            if definition.get("required", False) and value in (None, ""):
                errors.append(f"Missing required path parameter '{name}'.")
            elif value is not None:
                errors.extend(self._schema_errors(definition.get("schema", {}), value, prefix=f"path.{name}"))

        for name, definition in query_defs.items():
            if definition.get("required", False) and call.query_params.get(name) is None:
                errors.append(f"Missing required query parameter '{name}'.")

        unexpected_path = sorted(set(call.path_params) - set(path_defs))
        if unexpected_path:
            errors.append(f"Unexpected path parameter(s): {', '.join(unexpected_path)}")

        unexpected_query = sorted(set(call.query_params) - set(query_defs))
        if unexpected_query:
            errors.append(f"Unexpected query parameter(s): {', '.join(unexpected_query)}")

        for name, value in call.query_params.items():
            if name not in query_defs or value is None:
                continue
            schema = query_defs[name].get("schema", {})
            errors.extend(self._schema_errors(schema, value, prefix=f"query.{name}"))

        request_body = contract.get("request_body")
        if request_body:
            if request_body.get("required", False) and call.body is None:
                errors.append("Missing required JSON request body.")
            elif call.body is not None:
                schema = (
                    request_body.get("content", {})
                    .get("application/json", {})
                    .get("schema", {})
                )
                errors.extend(self._schema_errors(schema, call.body, prefix="body"))
        elif call.body not in (None, {}, []):
            errors.append("This operation does not accept a request body.")

        return errors

    def validate_response(self, operation_id: str, status_code: int, data: Any) -> list[str]:
        operation = self.digest.get_operation(operation_id)
        if not operation:
            return []
        responses = operation.get("contract", {}).get("responses", {})
        response = responses.get(str(status_code))
        if not response:
            return []
        schema = (
            response.get("content", {})
            .get("application/json", {})
            .get("schema")
        )
        if not schema:
            return []
        return self._schema_errors(schema, data, prefix="response")

    def _expand_refs(self, value: Any, seen: tuple[str, ...] = ()) -> Any:
        """Resolve the local OpenAPI component refs embedded in the digest."""
        if isinstance(value, list):
            return [self._expand_refs(item, seen) for item in value]
        if not isinstance(value, dict):
            return value

        ref = value.get("$ref")
        prefix = "#/components/schemas/"
        if isinstance(ref, str) and ref.startswith(prefix):
            name = ref[len(prefix):]
            if name in seen:
                # The current digest has no recursive schemas; fail clearly if one is added later.
                raise ValueError(f"Recursive schema reference is not supported: {' -> '.join((*seen, name))}")
            target = self.digest.schemas.get(name)
            if target is None:
                raise ValueError(f"Unknown schema reference: {ref}")
            merged = dict(target)
            merged.update({k: v for k, v in value.items() if k != "$ref"})
            return self._expand_refs(merged, (*seen, name))

        return {key: self._expand_refs(child, seen) for key, child in value.items()}

    def _schema_errors(self, schema: dict[str, Any], instance: Any, prefix: str) -> list[str]:
        if not schema:
            return []
        try:
            expanded = self._expand_refs(schema)
            validator = Draft202012Validator(expanded)
            found = sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
            result = []
            for error in found:
                path = ".".join(str(p) for p in error.path)
                location = f"{prefix}.{path}" if path else prefix
                result.append(f"{location}: {error.message}")
            return result
        except Exception as exc:  # validation should fail closed but explain why
            return [f"{prefix}: schema validation could not be completed: {exc}"]
