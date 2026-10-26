from pathlib import Path
from typing import List, Dict, Any, Optional
import httpx
from src.config import API_BASE_URL


class ApiClient:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)

    def health_check(self) -> bool:
        try:
            r = self.client.get("/api/health", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    def get_books(self) -> List[Dict[str, Any]]:
        try:
            r = self.client.get("/api/books")
            r.raise_for_status()
            return r.json().get("books", [])
        except Exception as e:
            print(f"[ApiClient] 获取书籍列表失败: {e}")
            return []

    def get_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        try:
            r = self.client.get(f"/api/books/{book_id}")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[ApiClient] 获取书籍详情失败: {e}")
            return None

    def upload_book(self, file_path: str) -> Optional[Dict[str, Any]]:
        path = Path(file_path)
        if not path.exists() or not path.suffix.lower() == ".pdf":
            raise ValueError("请选择有效的 PDF 文件")
            
        with open(path, "rb") as f:
            files = {"file": (path.name, f, "application/pdf")}
            r = self.client.post("/api/books/upload", files=files, timeout=60.0)
            r.raise_for_status()
            return r.json()

    def update_progress(self, book_id: int, current_page: int, total_pages: int) -> bool:
        try:
            r = self.client.post(
                f"/api/books/{book_id}/progress",
                json={"current_page": current_page, "total_pages": total_pages}
            )
            return r.status_code == 200
        except Exception as e:
            print(f"[ApiClient] 更新阅读进度失败: {e}")
            return False

    def delete_book(self, book_id: int) -> bool:
        try:
            r = self.client.delete(f"/api/books/{book_id}")
            return r.status_code == 200
        except Exception as e:
            print(f"[ApiClient] 删除书籍失败: {e}")
            return False

    def add_note(self, book_id: int, book_title: str, page_num: int, content: str) -> Optional[int]:
        try:
            r = self.client.post("/api/notes", json={
                "book_id": book_id,
                "book_title": book_title,
                "page_num": page_num,
                "content": content
            })
            r.raise_for_status()
            return r.json().get("note_id")
        except Exception as e:
            print(f"[ApiClient] 添加笔记失败: {e}")
            return None

    def get_notes(self, book_id: Optional[int] = None) -> List[Dict[str, Any]]:
        try:
            params = {}
            if book_id is not None:
                params["book_id"] = book_id
            r = self.client.get("/api/notes", params=params)
            r.raise_for_status()
            return r.json().get("notes", [])
        except Exception as e:
            print(f"[ApiClient] 获取笔记失败: {e}")
            return []

    def delete_note(self, note_id: int) -> bool:
        try:
            r = self.client.delete(f"/api/notes/{note_id}")
            return r.status_code == 200
        except Exception as e:
            print(f"[ApiClient] 删除笔记失败: {e}")
            return False


# 全局单例
api_client = ApiClient()
