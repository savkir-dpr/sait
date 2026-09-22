"""Надёжная отправка телеметрии Raspberry Pi в HTTP API.

Модуль не зависит от GUI и оборудования. Его можно безопасно вызывать из
CustomTkinter: сетевой запрос выполняется в фоновом потоке, а неотправленные
сообщения сохраняются в JSONL-очереди рядом с приложением.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

DEFAULT_INTERVAL_SECONDS = 60
Transport = Callable[[str, bytes, dict[str, str], float], None]


@dataclass(frozen=True)
class TelemetryConfig:
    """Настройки подключения одного устройства."""

    device_id: str
    endpoint: str
    api_key: str
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    queue_path: str = "telemetry_queue.jsonl"
    timeout_seconds: float = 10.0

    @classmethod
    def from_file(cls, path: str | os.PathLike[str]) -> "TelemetryConfig":
        with open(path, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)

        if not isinstance(data, dict):
            raise ValueError("Конфигурация телеметрии должна быть JSON-объектом")

        device_id = str(data.get("device_id", "")).strip()
        endpoint = str(data.get("endpoint", "")).strip()
        api_key = str(data.get("api_key", "")).strip()
        if not device_id:
            raise ValueError("В конфигурации отсутствует device_id")

        interval_seconds = int(data.get("interval_seconds", DEFAULT_INTERVAL_SECONDS))
        if interval_seconds < 1:
            raise ValueError("interval_seconds должен быть не меньше 1")

        return cls(
            device_id=device_id,
            endpoint=endpoint,
            api_key=api_key,
            interval_seconds=interval_seconds,
            queue_path=str(data.get("queue_path", "telemetry_queue.jsonl")),
            timeout_seconds=float(data.get("timeout_seconds", 10.0)),
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _http_transport(endpoint: str, payload: bytes, headers: dict[str, str], timeout: float) -> None:
    request = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if not 200 <= response.status < 300:
            raise urllib.error.HTTPError(endpoint, response.status, "Unexpected HTTP status", response.headers, None)


class TelemetryPublisher:
    """Отправляет измерения не чаще заданного интервала и не теряет их при сбое сети."""

    def __init__(self, config: TelemetryConfig, transport: Transport = _http_transport):
        self._config = config
        self._transport = transport
        self._last_publish_monotonic: float | None = None
        self._lock = threading.Lock()
        self._sending = False

    def publish_measurement(
        self,
        *,
        temperatures_c: dict[str, float | None],
        vacuum_kpa: float | None,
        absolute_pressure_kpa: float | None,
        doors_closed: dict[str, bool | None] | None = None,
        status: str = "online",
        monotonic_seconds: float | None = None,
    ) -> bool:
        """Поставить измерение в очередь, если прошла минута.

        Возвращает ``True``, если сообщение принято для фоновой отправки.
        ``monotonic_seconds`` используется тестами; в приложении его передавать не нужно.
        """
        import time

        now = time.monotonic() if monotonic_seconds is None else monotonic_seconds
        with self._lock:
            if self._last_publish_monotonic is not None and now - self._last_publish_monotonic < self._config.interval_seconds:
                return False
            self._last_publish_monotonic = now
            message: dict[str, Any] = {
                "type": "measurement",
                "device_id": self._config.device_id,
                "timestamp": _utc_now(),
                "status": status,
                "temperatures_c": temperatures_c,
                "vacuum_kpa": vacuum_kpa,
                "absolute_pressure_kpa": absolute_pressure_kpa,
            }
            if doors_closed is not None:
                message["doors_closed"] = doors_closed
            self._append_to_queue(message)
            self._start_sender_locked()
        return True

    def publish_event(self, *, action: str, program: str, details: str = "") -> None:
        """Поставить событие журнала в очередь без ограничения раз в минуту."""
        message = {
            "type": "event",
            "device_id": self._config.device_id,
            "timestamp": _utc_now(),
            "action": action,
            "program": program,
            "details": details,
        }
        with self._lock:
            self._append_to_queue(message)
            self._start_sender_locked()

    def _queue_file(self) -> Path:
        return Path(self._config.queue_path)

    def _append_to_queue(self, message: dict[str, Any]) -> None:
        queue_file = self._queue_file()
        queue_file.parent.mkdir(parents=True, exist_ok=True)
        with queue_file.open("a", encoding="utf-8") as queue:
            queue.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")

    def _start_sender_locked(self) -> None:
        if self._sending or not self._config.endpoint:
            return
        self._sending = True
        threading.Thread(target=self._flush_queue, name="telemetry-sender", daemon=True).start()

    def _flush_queue(self) -> None:
        try:
            while True:
                with self._lock:
                    messages = self._read_queue()
                if not messages:
                    return

                payload = json.dumps(messages[0], ensure_ascii=False).encode("utf-8")
                headers = {"Content-Type": "application/json"}
                if self._config.api_key:
                    headers["Authorization"] = f"Bearer {self._config.api_key}"
                try:
                    self._transport(self._config.endpoint, payload, headers, self._config.timeout_seconds)
                except Exception as exc:
                    print(f"Телеметрия не отправлена: {exc}")
                    return

                with self._lock:
                    remaining = self._read_queue()
                    self._write_queue(remaining[1:])
        finally:
            with self._lock:
                self._sending = False

    def _read_queue(self) -> list[dict[str, Any]]:
        queue_file = self._queue_file()
        if not queue_file.exists():
            return []
        messages = []
        with queue_file.open("r", encoding="utf-8") as queue:
            for line in queue:
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    messages.append(value)
        return messages

    def _write_queue(self, messages: list[dict[str, Any]]) -> None:
        queue_file = self._queue_file()
        temporary_file = queue_file.with_suffix(queue_file.suffix + ".tmp")
        with temporary_file.open("w", encoding="utf-8") as queue:
            for message in messages:
                queue.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
        temporary_file.replace(queue_file)
