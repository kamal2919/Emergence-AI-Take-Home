"""Small, provider-neutral LLM adapter for evidence-grounded memo synthesis."""

from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Protocol

from .models import Candidate


class LLMError(RuntimeError):
    """Raised when a configured model cannot return a valid, grounded response."""


@dataclass(frozen=True)
class LLMConfig:
    """Configuration for a Chat Completions-compatible endpoint."""

    endpoint: str
    model: str
    api_key_env: str = "SIGNALDESK_LLM_API_KEY"


@dataclass(frozen=True)
class Enrichment:
    team_summary: str
    product_summary: str
    market_summary: str
    risks: list[str]
    open_questions: list[str]
    source_urls: list[str]
    provider: str
    model: str

    @classmethod
    def from_response(
        cls,
        response: dict[str, Any],
        candidate: Candidate,
        provider: str,
        model: str,
    ) -> "Enrichment":
        required = {
            "team_summary",
            "product_summary",
            "market_summary",
            "risks",
            "open_questions",
            "source_urls",
        }
        if missing := required - response.keys():
            raise LLMError(f"LLM response is missing fields: {sorted(missing)}")
        summary_fields = ("team_summary", "product_summary", "market_summary")
        if not all(isinstance(response[key], str) and response[key].strip() for key in summary_fields):
            raise LLMError("LLM response contains a blank summary")
        list_fields = ("risks", "open_questions", "source_urls")
        if not all(
            isinstance(response[key], list)
            and all(isinstance(item, str) and item.strip() for item in response[key])
            for key in list_fields
        ):
            raise LLMError("LLM response has malformed list fields")
        allowed_urls = {item.source_url for item in candidate.evidence} | {candidate.website}
        if not set(response["source_urls"]).issubset(allowed_urls):
            raise LLMError("LLM cited a URL outside the supplied evidence")
        if candidate.source_url not in response["source_urls"]:
            raise LLMError("LLM response must cite the candidate source page")
        return cls(
            team_summary=response["team_summary"].strip(),
            product_summary=response["product_summary"].strip(),
            market_summary=response["market_summary"].strip(),
            risks=response["risks"],
            open_questions=response["open_questions"],
            source_urls=response["source_urls"],
            provider=provider,
            model=model,
        )

    def as_dict(self) -> dict:
        return asdict(self)


class Transport(Protocol):
    def post_json(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> dict[str, Any]: ...


class UrllibTransport:
    _MAX_ATTEMPTS = 3
    _RETRYABLE_STATUS_CODES = {500, 502, 503, 504}

    def post_json(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        for attempt in range(self._MAX_ATTEMPTS):
            try:
                with urllib.request.urlopen(request, timeout=45, context=_ssl_context()) as response:
                    return json.loads(response.read())
            except urllib.error.HTTPError as error:
                body = error.read().decode(errors="replace")[:500]
                if error.code in self._RETRYABLE_STATUS_CODES and attempt < self._MAX_ATTEMPTS - 1:
                    time.sleep(2**attempt)
                    continue
                raise LLMError(f"LLM API returned HTTP {error.code}: {body}") from error
            except urllib.error.URLError as error:
                raise LLMError(f"Could not reach LLM API: {error.reason}") from error
        raise AssertionError("LLM retry loop exited unexpectedly")


class OpenAICompatibleClient:
    """Calls a chat-completions-compatible endpoint using only the standard library."""

    def __init__(self, config: LLMConfig, transport: Transport | None = None):
        self.config = config
        self.transport = transport or UrllibTransport()

    def enrich(self, candidate: Candidate) -> Enrichment:
        api_key = os.getenv(self.config.api_key_env)
        if not api_key:
            raise LLMError(
                f"Set {self.config.api_key_env} before using --llm; never commit API keys."
            )
        evidence = _candidate_evidence(candidate)
        prompt = (
            "You are an investment-research synthesis assistant. Use ONLY the supplied evidence. "
            "Do not browse, infer private facts, invent metrics, or make an investment recommendation. "
            "Return strict JSON with exactly these keys: team_summary, product_summary, market_summary, "
            "risks (array of 2-4 strings), open_questions (array of 2-4 strings), source_urls (array). "
            "Every source_urls entry must be from evidence_records or website, and must include a source URL from evidence_records. "
            "Say 'not established in supplied evidence' where necessary. Evidence:\n"
            + json.dumps(evidence)
        )
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["team_summary", "product_summary", "market_summary", "risks", "open_questions", "source_urls"],
            "properties": {
                "team_summary": {"type": "string"}, "product_summary": {"type": "string"}, "market_summary": {"type": "string"},
                "risks": {"type": "array", "items": {"type": "string"}},
                "open_questions": {"type": "array", "items": {"type": "string"}},
                "source_urls": {"type": "array", "items": {"type": "string"}},
            },
        }
        payload = {
            "model": self.config.model,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "investment_evidence_synthesis",
                    "strict": True,
                    "schema": schema,
                },
            },
            "messages": [
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        response = self.transport.post_json(self.config.endpoint, headers, payload)
        try:
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise LLMError("LLM response was not a valid chat-completions JSON response") from error
        return Enrichment.from_response(
            parsed,
            candidate,
            provider=self.config.endpoint,
            model=self.config.model,
        )


def _ssl_context() -> ssl.SSLContext:
    ca_bundle = os.getenv("SIGNALDESK_CA_BUNDLE")
    return ssl.create_default_context(cafile=ca_bundle) if ca_bundle else ssl.create_default_context()


def _candidate_evidence(candidate: Candidate) -> dict[str, Any]:
    return {
        "name": candidate.name,
        "website": candidate.website,
        "description": candidate.description,
        "freshness_signal": candidate.freshness_signal,
        "founder_signal": candidate.founder_signal,
        "market_note": candidate.market_note,
        "risk_notes": candidate.risk_notes,
        "evidence_records": [asdict(item) for item in candidate.evidence],
    }
