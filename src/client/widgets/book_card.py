from pathlib import Path
from typing import Dict, Any
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QMenu, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QColor, QCursor, QFont


class BookCard(QFrame):
    clicked = Signal(int)  # book_id
    delete_requested = Signal(int)  # book_id

    def __init__(self, book: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.book = book
        self.book_id = book["id"]
        self.setObjectName("card")
        self.setFixedSize(190, 290)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # 1. 封面展示区
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(170, 180)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setStyleSheet("""
            QLabel {
                background-color: #12141A;
                border: 1px solid #232838;
                border-radius: 6px;
                color: #64748B;
            }
        """)

        cover_path = self.book.get("cover_path")
        if cover_path and Path(cover_path).exists():
            pix = QPixmap(cover_path)
            if not pix.isNull():
                scaled_pix = pix.scaled(
                    170, 180,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.cover_label.setPixmap(scaled_pix)
            else:
                self._set_fallback_cover()
        else:
            self._set_fallback_cover()

        layout.addWidget(self.cover_label)

        # 2. 书名
        title_text = self.book.get("title", "未命名书籍")
        self.title_label = QLabel(title_text)
        font = QFont()
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: #F8FAFC; font-size: 13px;")
        self.title_label.setWordWrap(False)
        self.title_label.setToolTip(title_text)
        layout.addWidget(self.title_label)

        # 3. 作者与页数
        author = self.book.get("author", "未知作者")
        pages = self.book.get("page_count", 0)
        info_label = QLabel(f"{author} · 共 {pages} 页")
        info_label.setStyleSheet("color: #64748B; font-size: 11px;")
        layout.addWidget(info_label)

        # 4. 阅读进度条与文本
        progress_val = float(self.book.get("reading_progress", 0.0))
        cur_page = self.book.get("current_page", 1)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(int(progress_val))
        layout.addWidget(progress_bar)

        progress_text = QLabel(f"进度: {progress_val:.0f}% (第 {cur_page} 页)")
        progress_text.setStyleSheet("color: #94A3B8; font-size: 10px;")
        layout.addWidget(progress_text)

    def _set_fallback_cover(self):
        title = self.book.get("title", "PDF")
        short_title = title[:8] + "..." if len(title) > 8 else title
        self.cover_label.setText(f"📄\n\n{short_title}")
        self.cover_label.setStyleSheet("""
            QLabel {
                background-color: #1A202C;
                border: 1px dashed #334155;
                border-radius: 6px;
                color: #94A3B8;
                font-weight: bold;
                font-size: 14px;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.book_id)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        open_action = menu.addAction("📖 打开阅读")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ 从书架删除")

        action = menu.exec(event.globalPos())
        if action == open_action:
            self.clicked.emit(self.book_id)
        elif action == delete_action:
            self.delete_requested.emit(self.book_id)
