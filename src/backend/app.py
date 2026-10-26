import json
import shutil
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from src.config import BOOKS_DIR, COVERS_DIR
from src.backend import db
from src.backend import pdf_service

# 初始化数据库
db.init_db()

app = FastAPI(title="My AI Library Backend", version="1.0.0")

# 允许跨域（方便未来 Web/多端扩展）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProgressUpdateRequest(BaseModel):
    current_page: int
    total_pages: int


class NoteCreateRequest(BaseModel):
    book_id: int
    book_title: str
    page_num: int
    content: str


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "My AI Library Server"}


@app.get("/api/books")
def list_books():
    books = db.get_all_books()
    # 解析 toc_json 为 list 便于使用
    for book in books:
        try:
            book["toc"] = json.loads(book.get("toc_json", "[]"))
        except Exception:
            book["toc"] = []
    return {"books": books}


@app.get("/api/books/{book_id}")
def get_book(book_id: int):
    book = db.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="书籍未找到")
    try:
        book["toc"] = json.loads(book.get("toc_json", "[]"))
    except Exception:
        book["toc"] = []
    return book


@app.post("/api/books/upload")
async def upload_book(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="目前仅支持上传 PDF 格式文件")
    
    file_bytes = await file.read()
    file_size = len(file_bytes)
    file_hash = pdf_service.calculate_file_hash(file_bytes)
    
    # 检查是否已存在相同文件
    existing_book = db.get_book_by_hash(file_hash)
    if existing_book:
        return {
            "message": "书籍已存在书架中",
            "book_id": existing_book["id"],
            "book": existing_book
        }
    
    # 保存文件
    safe_stem = Path(file.filename).stem[:50]
    save_filename = f"{safe_stem}_{file_hash[:8]}.pdf"
    save_path = BOOKS_DIR / save_filename
    with open(save_path, "wb") as f:
        f.write(file_bytes)
        
    try:
        # 解析 PDF 元信息、目录与封面
        info = pdf_service.process_pdf(save_path, file_hash)
        
        # 写入数据库
        book_id = db.add_book(
            title=info["title"],
            author=info["author"],
            file_name=file.filename,
            file_path=str(save_path),
            file_size=file_size,
            file_hash=file_hash,
            page_count=info["page_count"],
            cover_path=info["cover_path"],
            toc_json=info["toc_json"]
        )
        
        book = db.get_book_by_id(book_id)
        return {
            "message": "上传成功",
            "book_id": book_id,
            "book": book
        }
    except Exception as e:
        if save_path.exists():
            save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"PDF 解析失败: {str(e)}")


@app.get("/api/books/{book_id}/cover")
def get_book_cover(book_id: int):
    book = db.get_book_by_id(book_id)
    if not book or not book.get("cover_path"):
        raise HTTPException(status_code=404, detail="封面未找到")
    cover_file = Path(book["cover_path"])
    if not cover_file.exists():
        raise HTTPException(status_code=404, detail="封面文件不存在")
    return FileResponse(str(cover_file), media_type="image/png")


@app.get("/api/books/{book_id}/file")
def get_book_file(book_id: int):
    book = db.get_book_by_id(book_id)
    if not book or not book.get("file_path"):
        raise HTTPException(status_code=404, detail="书籍未找到")
    pdf_file = Path(book["file_path"])
    if not pdf_file.exists():
        raise HTTPException(status_code=404, detail="本地 PDF 文件不存在")
    return FileResponse(str(pdf_file), media_type="application/pdf", filename=book["file_name"])


@app.post("/api/books/{book_id}/progress")
def update_progress(book_id: int, payload: ProgressUpdateRequest):
    success = db.update_reading_progress(book_id, payload.current_page, payload.total_pages)
    if not success:
        raise HTTPException(status_code=404, detail="更新进度失败，书籍不存在")
    return {"status": "ok", "current_page": payload.current_page}


@app.delete("/api/books/{book_id}")
def delete_book(book_id: int):
    book = db.delete_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    
    # 异步清理物理文件
    if book.get("file_path") and Path(book["file_path"]).exists():
        try:
            Path(book["file_path"]).unlink(missing_ok=True)
        except Exception:
            pass
    if book.get("cover_path") and Path(book["cover_path"]).exists():
        try:
            Path(book["cover_path"]).unlink(missing_ok=True)
        except Exception:
            pass
    return {"status": "ok", "message": f"成功删除书籍: {book['title']}"}


# --- 笔记功能接口 ---

@app.get("/api/notes")
def list_notes(book_id: Optional[int] = None):
    notes = db.get_notes(book_id)
    return {"notes": notes}


@app.post("/api/notes")
def create_note(payload: NoteCreateRequest):
    note_id = db.add_note(
        book_id=payload.book_id,
        book_title=payload.book_title,
        page_num=payload.page_num,
        content=payload.content
    )
    return {"status": "ok", "note_id": note_id}


@app.delete("/api/notes/{note_id}")
def delete_note_endpoint(note_id: int):
    success = db.delete_note(note_id)
    if not success:
        raise HTTPException(status_code=404, detail="笔记未找到")
    return {"status": "ok", "message": "已删除笔记"}
