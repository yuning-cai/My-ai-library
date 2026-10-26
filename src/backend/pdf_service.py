import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import pymupdf as fitz
from src.config import COVERS_DIR, BOOKS_DIR


def calculate_file_hash(file_bytes: bytes) -> str:
    """计算文件 SHA256 哈希值"""
    return hashlib.sha256(file_bytes).hexdigest()


def process_pdf(pdf_path: Path, file_hash: str) -> Dict[str, Any]:
    """
    解析 PDF：提取元数据、大纲目录、并生成封面缩略图
    """
    doc = fitz.open(pdf_path)
    try:
        page_count = len(doc)
        metadata = doc.metadata or {}
        
        # 标题与作者
        raw_title = metadata.get("title", "").strip()
        title = raw_title if raw_title else pdf_path.stem
        raw_author = metadata.get("author", "").strip()
        author = raw_author if raw_author else "未知作者"
        
        # 提取目录 (TOC: [[lvl, title, page], ...])
        raw_toc = doc.get_toc()
        toc = []
        for item in raw_toc:
            if len(item) >= 3:
                toc.append({
                    "level": item[0],
                    "title": item[1].strip(),
                    "page": item[2]
                })
        
        # 生成并保存第 1 页封面缩略图
        cover_filename = f"cover_{file_hash[:16]}.png"
        cover_path = COVERS_DIR / cover_filename
        
        if page_count > 0:
            first_page = doc[0]
            # 缩放 1.5 倍渲染，保证封面清晰度
            pix = first_page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            pix.save(str(cover_path))
        else:
            cover_path = None

        return {
            "title": title,
            "author": author,
            "page_count": page_count,
            "toc": toc,
            "toc_json": json.dumps(toc, ensure_ascii=False),
            "cover_path": str(cover_path) if cover_path else None
        }
    finally:
        doc.close()


def extract_page_text(pdf_path: Path, page_index: int) -> str:
    """
    提取指定页面的纯文本（预留给后续大模型与划词问答）
    """
    doc = fitz.open(pdf_path)
    try:
        if 0 <= page_index < len(doc):
            return doc[page_index].get_text()
        return ""
    finally:
        doc.close()
