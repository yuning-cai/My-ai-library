import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.client.server_thread import BackgroundServer
from src.client.api_client import api_client
from src.client.main_window import MainWindow
from src.client.theme import DARK_THEME


def main():
    # 1. 启动后台 FastAPI 服务
    server = BackgroundServer()
    server.start()

    # 2. 等待服务健康检测通过 (最多 5 秒)
    start_time = time.time()
    server_ready = False
    while time.time() - start_time < 5.0:
        if api_client.health_check():
            server_ready = True
            break
        time.sleep(0.1)

    if not server_ready:
        print("[警告] FastAPI 本地服务启动响应较慢，桌面端将继续启动...")

    # 3. 启动桌面端 PySide6 GUI
    app = QApplication(sys.argv)
    app.setApplicationName("AI Library")
    app.setStyleSheet(DARK_THEME)

    window = MainWindow()
    window.show()

    try:
        exit_code = app.exec()
    finally:
        server.stop()
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
