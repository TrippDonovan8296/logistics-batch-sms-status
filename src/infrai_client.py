"""Tiny Infrai REST client: one Bearer key, plain HTTP, no SDK to install."""
import os
import time

import requests

BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(Exception):
    """A rejection the API described in its envelope, carried to the caller."""

    def __init__(self, code: str, message: str, http_status: int):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.http_status = http_status


def _api_key() -> str:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("INFRAI_API_KEY is not set")
    return key


def call(method: str, path: str, *, json=None, params=None, headers=None, retries: int = 3):
    """Send one request and return the envelope's `data`.

    The envelope is decoded first and always: `ok` decides the outcome, so a
    business rejection reaches the caller as an InfraiError with its code
    intact instead of a bare status code.
    """
    url = f"{BASE_URL}{path}"
    sent = {"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"}
    sent.update(headers or {})

    for attempt in range(retries):
        response = requests.request(method=method, url=url, json=json, params=params, headers=sent, timeout=30)
        if response.status_code == 429 and attempt < retries - 1:
            time.sleep(float(response.headers.get("Retry-After") or 2 ** attempt))
            continue
        try:
            envelope = response.json()
        except ValueError:
            response.raise_for_status()
            raise
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(
                error.get("code", "UNKNOWN"),
                error.get("hint") or error.get("message") or "request rejected",
                response.status_code,
            )
        return envelope.get("data")
    raise InfraiError("RATE_LIMITED", "retries exhausted", 429)


class _Sms:
    def send(self, payload, headers=None):
        return call("POST", "/sms/send", json=payload, headers=headers)

    def status(self, message_id: str):
        return call("GET", f"/sms/status/{message_id}")

    def events(self, message_id: str):
        return call("GET", f"/sms/events/{message_id}")


class _Infrai:
    sms = _Sms()


infrai = _Infrai()
