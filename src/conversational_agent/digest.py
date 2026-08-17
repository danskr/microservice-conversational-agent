from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .config import get_settings


_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "could", "do", "does", "for",
    "from", "how", "i", "in", "is", "it", "me", "my", "of", "on", "or", "please", "service",
    "that", "the", "this", "to", "what", "when", "where", "which", "with", "would", "you",
}


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9_\-]+", text.lower())
        if len(token) > 1 and token not in _STOP_WORDS
    }


@dataclass(frozen=True)
class DigestSnippet:
    section: str
    key: str
    value: Any
    searchable_text: str


class DigestStore:
    """Loads the single canonical YAML digest and exposes safe semantic lookups."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        with self.path.open("r", encoding="utf-8") as handle:
            self.data: dict[str, Any] = yaml.safe_load(handle)
        self._validate_minimum_shape()
        self._snippets = self._build_snippets()

    def _validate_minimum_shape(self) -> None:
        required = {
            "digest",
            "agent_index",
            "service",
            "domain",
            "operations",
            "workflows",
            "errors",
            "conversation",
            "execution_policy",
            "api_contract",
        }
        missing = sorted(required - set(self.data))
        if missing:
            raise ValueError(f"Service digest is missing required sections: {missing}")
        if not self.data["operations"]:
            raise ValueError("Service digest contains no operations")

    @property
    def operations(self) -> dict[str, Any]:
        return self.data["operations"]

    @property
    def schemas(self) -> dict[str, Any]:
        return self.data["api_contract"]["schemas"]

    def get_operation(self, operation_id: str) -> dict[str, Any] | None:
        return self.operations.get(operation_id)

    def compact_operation_catalog(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for operation_id, spec in self.operations.items():
            execution = spec.get("execution", {})
            contract = spec.get("contract", {})
            result.append(
                {
                    "operation_id": operation_id,
                    "method": spec["http"]["method"],
                    "path": spec["http"]["path"],
                    "purpose": spec.get("purpose", ""),
                    "parameters": contract.get("parameters", []),
                    "request_body": contract.get("request_body"),
                    "effect": execution.get("effect", "unknown"),
                    "risk": execution.get("risk", "unknown"),
                    "confirmation": execution.get("confirmation", "unknown"),
                    "conversation_hints": spec.get("conversation_hints", []),
                }
            )
        return result

    def _build_snippets(self) -> list[DigestSnippet]:
        snippets: list[DigestSnippet] = []
        section_keys = [
            "operations",
            "workflows",
            "business_rules",
            "state_machines",
            "business_events",
        ]
        for section in section_keys:
            values = self.data.get(section, {})
            if isinstance(values, dict):
                for key, value in values.items():
                    searchable = f"{section} {key} {yaml.safe_dump(value, sort_keys=False)}"
                    snippets.append(DigestSnippet(section, str(key), value, searchable.lower()))

        entities = self.data.get("domain", {}).get("entities", {})
        for key, value in entities.items():
            searchable = f"domain entity {key} {yaml.safe_dump(value, sort_keys=False)}"
            snippets.append(DigestSnippet("domain.entities", str(key), value, searchable.lower()))

        enums = self.data.get("domain", {}).get("enums", {})
        for key, value in enums.items():
            searchable = f"domain enum {key} {yaml.safe_dump(value, sort_keys=False)}"
            snippets.append(DigestSnippet("domain.enums", str(key), value, searchable.lower()))

        errors = self.data.get("errors", {}).get("catalog", {})
        for key, value in errors.items():
            searchable = f"error {key} {yaml.safe_dump(value, sort_keys=False)}"
            snippets.append(DigestSnippet("errors.catalog", str(key), value, searchable.lower()))

        return snippets

    def search(self, query: str, limit: int | None = None) -> list[DigestSnippet]:
        limit = limit or get_settings().max_digest_snippets
        query_l = query.lower()
        query_tokens = _tokens(query)
        scored: list[tuple[float, DigestSnippet]] = []
        for snippet in self._snippets:
            snippet_tokens = _tokens(snippet.searchable_text)
            overlap = query_tokens & snippet_tokens
            score = float(len(overlap) * 3)
            key_l = snippet.key.lower()
            if key_l in query_l or query_l in key_l:
                score += 10
            # Give exact operation/error vocabulary strong weight.
            for token in query_tokens:
                if token in key_l:
                    score += 2
            if score > 0:
                scored.append((score, snippet))
        scored.sort(key=lambda item: (-item[0], item[1].section, item[1].key))
        return [snippet for _, snippet in scored[:limit]]

    def planner_context(self, query: str) -> str:
        """Return focused YAML context plus the complete compact operation catalog."""
        relevant = self.search(query)
        focused = [
            {"section": s.section, "key": s.key, "value": s.value}
            for s in relevant
        ]
        payload = {
            "service": self.data["service"],
            "agent_index": self.data["agent_index"],
            "operation_catalog": self.compact_operation_catalog(),
            "api_schemas": self.data.get("api_contract", {}).get("schemas", {}),
            "conversation_rules": self.data.get("conversation", {}),
            "execution_policy": self.data.get("execution_policy", {}),
            "relevant_digest_sections": focused,
        }
        return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)

    def operation_yaml(self, operation_id: str) -> str:
        spec = self.get_operation(operation_id)
        if spec is None:
            return ""
        return yaml.safe_dump({"operation_id": operation_id, **spec}, sort_keys=False, allow_unicode=True)


_store: DigestStore | None = None


def get_digest_store() -> DigestStore:
    global _store
    if _store is None:
        _store = DigestStore(get_settings().digest_path)
    return _store
