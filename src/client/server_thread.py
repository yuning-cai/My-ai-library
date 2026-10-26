import threading
import time
import uvicorn
from src.config import SERVER_HOST, SERVER_PORT


class BackgroundServer:
    def __init__(self, host: str = SERVER_HOST, port: int = SERVER_PORT):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None

    def _run(self):
        config = uvicorn.Config(
            "src.backend.app:app",
            host=self.host,
            port=self.port,
            log_level="error",
            access_log=False
        )
        self.server = uvicorn.Server(config)
        self.server.run()

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        # 等待服务就绪
        time.sleep(0.5)

    def stop(self):
        if self.server:
            self.server.should_exit = True
