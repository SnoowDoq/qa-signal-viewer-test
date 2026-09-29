"""
Драйвер главного окна приложения через UI Automation (pywinauto, backend "uia").

Qt 5.x/6.x отдаёт виджеты в UIA: кнопки — Button, QTableWidget — Table,
ячейки — DataItem. Тест работает только с этим классом и не знает деталей
поиска элементов — при изменении UI правится одно место.
"""

import time
from dataclasses import dataclass

from pywinauto import Application

WINDOW_TITLE = "Signal Viewer"
COLUMNS = ["ID", "Имя", "Значение", "Качество", "Время"]


@dataclass
class Row:
    id: str
    name: str
    value: str
    quality: str
    time: str


class SignalViewerApp:
    def __init__(self, cmdline: str, timeout: float = 15):
        # wait_for_idle=False: при запуске через python.exe процесс консольный,
        # WaitForInputIdle для него падает; готовность окна ждём ниже явно
        self.app = Application(backend="uia").start(cmdline, timeout=timeout, wait_for_idle=False)
        self.window = self.app.window(title=WINDOW_TITLE)
        self.window.wait("visible ready", timeout=timeout)

    def close(self):
        try:
            self.app.kill()
        except Exception:
            pass

    # ---------- действия ----------

    def click_connect(self):
        self.window.child_window(title="Подключиться", control_type="Button").click_input()

    def click_refresh(self):
        self.window.child_window(title="Обновить", control_type="Button").click_input()

    # ---------- чтение ----------

    def header(self) -> list[str]:
        table = self.window.child_window(control_type="Table")
        return [h.window_text() for h in table.children(control_type="Header")]

    def read_table(self) -> list[Row]:
        """Читает все строки таблицы как текст — ровно то, что видит оператор."""
        table = self.window.child_window(control_type="Table")
        texts = [c.window_text() for c in table.descendants(control_type="DataItem")]
        n = len(COLUMNS)
        return [Row(*texts[i:i + n]) for i in range(0, len(texts) - len(texts) % n, n)]

    def wait_table(self, condition, timeout: float = 5, interval: float = 0.2) -> list[Row]:
        """Ждёт, пока содержимое таблицы удовлетворит условию (UI обновляется асинхронно)."""
        deadline = time.monotonic() + timeout
        rows = self.read_table()
        while not condition(rows) and time.monotonic() < deadline:
            time.sleep(interval)
            rows = self.read_table()
        return rows
