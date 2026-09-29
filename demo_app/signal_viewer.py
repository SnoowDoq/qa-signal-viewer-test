"""
Демо-заглушка тестируемого приложения (PySide6/Qt).

НЕ является частью решения — реального приложения у меня нет, поэтому эта
минимальная копия интерфейса из условия нужна только затем, чтобы автотест
можно было запустить "из коробки". Для прогона на настоящем приложении
укажите путь к нему в переменной окружения APP_PATH.
"""

import json
import socket
import sys
from datetime import datetime

from PySide6.QtWidgets import (QApplication, QHBoxLayout, QMainWindow, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

HOST, PORT = "127.0.0.1", 2001
COLUMNS = ["ID", "Имя", "Значение", "Качество", "Время"]


class SignalViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Signal Viewer")
        self.resize(700, 420)
        self.sock = None
        self.stream = None

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.connect_btn = QPushButton("Подключиться")
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.setEnabled(False)
        self.connect_btn.clicked.connect(self.on_connect)
        self.refresh_btn.clicked.connect(self.on_refresh)

        buttons = QHBoxLayout()
        buttons.addWidget(self.connect_btn)
        buttons.addWidget(self.refresh_btn)
        layout = QVBoxLayout()
        layout.addLayout(buttons)
        layout.addWidget(self.table)
        root = QWidget()
        root.setLayout(layout)
        self.setCentralWidget(root)

    def on_connect(self):
        try:
            self.sock = socket.create_connection((HOST, PORT), timeout=3)
            self.stream = self.sock.makefile("rwb")
        except OSError as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться: {e}")
            return
        self.refresh_btn.setEnabled(True)
        self.on_refresh()

    def on_refresh(self):
        self.stream.write(b"GET\n")
        self.stream.flush()
        signals = json.loads(self.stream.readline())["signals"]
        self.table.setRowCount(len(signals))
        for row, s in enumerate(signals):
            ts = datetime.fromisoformat(s["timestamp"].replace("Z", "+00:00"))
            cells = [str(s["id"]), s["name"], f"{s['value']:.3f}", s["quality"],
                     ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]]
            for col, text in enumerate(cells):
                self.table.setItem(row, col, QTableWidgetItem(text))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SignalViewer()
    w.show()
    sys.exit(app.exec())
