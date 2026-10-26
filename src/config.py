import os
from pathlib import Path

# 项目根路径
ROOT_DIR = Path(__file__).resolve().parent.parent

# 存储路径
STORAGE_DIR = ROOT_DIR / "storage"
BOOKS_DIR = STORAGE_DIR / "books"
COVERS_DIR = STORAGE_DIR / "covers"
DB_PATH = STORAGE_DIR / "library.db"

# 确保存储目录存在
BOOKS_DIR.mkdir(parents=True, exist_ok=True)
COVERS_DIR.mkdir(parents=True, exist_ok=True)

# 本地服务配置
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8765
API_BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
