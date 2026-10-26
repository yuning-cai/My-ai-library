import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from src.config import DB_PATH


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库结构"""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT DEFAULT '未知作者',
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                file_hash TEXT UNIQUE,
                page_count INTEGER DEFAULT 0,
                cover_path TEXT,
                current_page INTEGER DEFAULT 1,
                reading_progress REAL DEFAULT 0.0,
                toc_json TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                last_read_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                book_title TEXT NOT NULL,
                page_num INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


def get_all_books() -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books ORDER BY id DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_book_by_id(book_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_book_by_hash(file_hash: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books WHERE file_hash = ?", (file_hash,))
        row = cursor.fetchone()
        return dict(row) if row else None


def add_book(
    title: str,
    author: str,
    file_name: str,
    file_path: str,
    file_size: int,
    file_hash: str,
    page_count: int,
    cover_path: Optional[str] = None,
    toc_json: str = "[]"
) -> int:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO books (
                title, author, file_name, file_path, file_size, file_hash,
                page_count, cover_path, current_page, reading_progress,
                toc_json, created_at, last_read_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0.0, ?, ?, ?)
        """, (
            title, author, file_name, file_path, file_size, file_hash,
            page_count, cover_path, toc_json, now_str, now_str
        ))
        conn.commit()
        return cursor.lastrowid


def update_reading_progress(book_id: int, current_page: int, total_pages: int) -> bool:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    progress = round((current_page / max(1, total_pages)) * 100.0, 1)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE books 
            SET current_page = ?, reading_progress = ?, last_read_at = ?
            WHERE id = ?
        """, (current_page, progress, now_str, book_id))
        conn.commit()
        return cursor.rowcount > 0


def delete_book(book_id: int) -> Optional[Dict[str, Any]]:
    book = get_book_by_id(book_id)
    if not book:
        return None
    with get_db() as conn:
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.execute("DELETE FROM notes WHERE book_id = ?", (book_id,))
        conn.commit()
    return book


def add_note(book_id: int, book_title: str, page_num: int, content: str) -> int:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notes (book_id, book_title, page_num, content, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (book_id, book_title, page_num, content, now_str))
        conn.commit()
        return cursor.lastrowid


def get_notes(book_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        if book_id is not None:
            cursor.execute("SELECT * FROM notes WHERE book_id = ? ORDER BY id DESC", (book_id,))
        else:
            cursor.execute("SELECT * FROM notes ORDER BY id DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def delete_note(note_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        return cursor.rowcount > 0


# 模块加载时自动初始化表结构
init_db()
