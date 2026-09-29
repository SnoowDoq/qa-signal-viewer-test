import os
import sys
import time
from pathlib import Path

import pytest

from app_driver import SignalViewerApp
from fake_service import FakeSignalService

ROOT = Path(__file__).resolve().parent.parent
# Путь к тестируемому приложению. По умолчанию — демо-заглушка из demo_app/,
# для реального приложения: set APP_PATH=C:\path\to\SignalViewer.exe
APP_CMD = os.environ.get("APP_PATH") or f'"{sys.executable}" "{ROOT / "demo_app" / "signal_viewer.py"}"'
SERVICE_PORT = int(os.environ.get("SERVICE_PORT", 2001))


@pytest.fixture
def service():
    """Поднимает управляемый симулятор на порту 2001 и гасит его после теста."""
    svc = FakeSignalService(port=SERVICE_PORT)
    svc.start()
    yield svc
    svc.stop()


@pytest.fixture
def app(service):
    """Запускает приложение (после сервиса) и закрывает его после теста."""
    viewer = SignalViewerApp(APP_CMD)
    yield viewer
    viewer.close()


def wait_for(predicate, timeout: float = 5, interval: float = 0.1) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()
