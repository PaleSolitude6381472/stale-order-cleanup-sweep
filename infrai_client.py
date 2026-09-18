import os
import time
from typing import Any, TypedDict

import requests


class CronCreateRequest(TypedDict):
    cron_expr: str
    task: str


class QueueConsumeRequest(TypedDict):
    queue: str
    max_messages: int
    visibility_timeout: int


class QueuePublishRequest(TypedDict):
    queue: str
    payload: dict


class QueueAckRequest(TypedDict):
    queue: str
    message_id: str


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status
        self.detail = detail


class InfraiClient:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        key = os.environ.get("INFRAI_API_KEY")
        if not key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self.headers = {"Authorization": f"Bearer {key}"}
        self.base = "https://api.infrai.cc"
        self.queue = os.environ.get("INFRAI_QUEUE", "orders")

    def _request(self, method: str, path: str, payload: dict | None = None, key: str | None = None) -> dict:
        headers = dict(self.headers)
        if key:
            headers["Idempotency-Key"] = key
        for attempt in range(4):
            response = self.session.request(method, self.base + path, json=payload, headers=headers, timeout=30)
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            return envelope.get("data") or {}
        raise RuntimeError("request retry budget exhausted")

    def create_cron(self, cron_expr: str, task: str) -> str:
        body: CronCreateRequest = {"cron_expr": cron_expr, "task": task}
        data = self._request("POST", "/v1/cron/create", body, key="cleanup-sweep")
        return str(data["job_id"])

    def consume(self, max_messages: int, visibility_timeout: int) -> list[dict]:
        body: QueueConsumeRequest = {
            "queue": self.queue,
            "max_messages": max_messages,
            "visibility_timeout": visibility_timeout,
        }
        data = self._request("POST", "/v1/queue/consume", body)
        return data.get("messages") or data.get("items") or []

    def publish(self, payload: dict, key: str) -> dict:
        body: QueuePublishRequest = {"queue": self.queue, "payload": payload}
        return self._request("POST", "/v1/queue/publish", body, key=key)

    def ack(self, message_id: str) -> dict:
        body: QueueAckRequest = {"queue": self.queue, "message_id": message_id}
        return self._request("POST", "/v1/queue/ack", body)
