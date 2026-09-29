"""
Управляемый сервис-симулятор сигналов для автотестов.

Зачем свой симулятор, а не штатный:
штатный симулятор генерирует значения сам, и тест не знает, что именно он
отправил. Чтобы проверить КОРРЕКТНОСТЬ отображения, тесту нужен "эталон" —
точные данные, которые ушли в приложение. Этот симулятор повторяет поведение
штатного (10 сигналов, синусоида/случайные значения, порт 2001), но
запоминает каждый отправленный снимок, и тест сравнивает с ним таблицу.

Протокол (допущение — в условии задачи не описан, при наличии спецификации
меняется только _handle_client / _make_snapshot):
    клиент -> сервис:  "GET\n"
    сервис -> клиент:  одна строка JSON + "\n":
        {"signals": [{"id": 1, "name": "Signal_01", "value": 12.345,
                      "quality": "GOOD", "timestamp": "2026-09-29T10:00:00.123Z"}, ...]}
"""

import json
import math
import random
import socket
import threading
import time
from datetime import datetime, timezone

SIGNAL_COUNT = 10


class FakeSignalService:
    def __init__(self, host: str = "127.0.0.1", port: int = 2001):
        self.host = host
        self.port = port
        self.request_count = 0          # сколько запросов GET обслужено
        self.last_snapshot = None       # последний отправленный снимок (эталон для теста)
        self._lock = threading.Lock()
        self._server = None
        self._stopped = threading.Event()
        self._t0 = time.monotonic()

    # ---------- жизненный цикл ----------

    def start(self):
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, self.port))
        self._server.listen()
        self._server.settimeout(0.2)  # чтобы accept не блокировал остановку
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def stop(self):
        self._stopped.set()
        if self._server:
            self._server.close()

    # ---------- генерация данных ----------

    def _make_snapshot(self) -> list[dict]:
        """10 сигналов: нечётные ID — синусоида, чётные — случайные значения."""
        t = time.monotonic() - self._t0
        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        signals = []
        for i in range(1, SIGNAL_COUNT + 1):
            if i % 2:
                value = 100 * math.sin(t + i)
            else:
                value = random.uniform(-500, 500)
            signals.append({
                "id": i,
                "name": f"Signal_{i:02d}",
                # округляем до 3 знаков — столько же показывает UI,
                # иначе сравнение упрётся в округление отображения, а не в баг
                "value": round(value, 3),
                "quality": "GOOD",
                "timestamp": ts,
            })
        return signals

    # ---------- сеть ----------

    def _accept_loop(self):
        while not self._stopped.is_set():
            try:
                conn, _ = self._server.accept()
            except (socket.timeout, OSError):
                continue
            threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()

    def _handle_client(self, conn: socket.socket):
        with conn, conn.makefile("rwb") as stream:
            for raw in stream:
                if raw.strip() != b"GET":
                    continue
                snapshot = self._make_snapshot()
                with self._lock:
                    self.last_snapshot = snapshot
                    self.request_count += 1
                stream.write(json.dumps({"signals": snapshot}).encode() + b"\n")
                stream.flush()
