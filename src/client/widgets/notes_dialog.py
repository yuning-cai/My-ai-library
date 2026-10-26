from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QComboBox, QMessageBox,
    QApplication
)
from PySide6.QtCore import Qt, Signal
from src.client.api_client import api_client


class NoteCard(QFrame):
    jump_requested = Signal(int, int)  # book_id, page_num
    deleted = Signal(int)  # note_id

    def __init__(self, note: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.note = note
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QFrame#noteCard {
                background-color: #1A1E29;
                border: 1px solid #2B3347;
                border-radius: 8px;
                padding: 8px;
            }
            QFrame#noteCard:hover {
                border-color: #3B82F6;
            }
        """)
        self.setObjectName("noteCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # 1. 顶部信息栏
        header = QHBoxLayout()
        book_title = QLabel(f"📖 {self.note.get('book_title', '未知书籍')}")
        book_title.setStyleSheet("font-weight: bold; color: #60A5FA; font-size: 13px;")
        header.addWidget(book_title)

        page_badge = QLabel(f"第 {self.note.get('page_num', 1)} 页")
        page_badge.setStyleSheet("""
            background-color: #1E293B;
            color: #38BDF8;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        """)
        header.addWidget(page_badge)

        header.addStretch()

        time_lbl = QLabel(self.note.get("created_at", ""))
        time_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
        header.addWidget(time_lbl)

        layout.addLayout(header)

        # 2. 笔记引用正文
        content_box = QLabel(self.note.get("content", ""))
        content_box.setWordWrap(True)
        content_box.setTextInteractionFlags(Qt.TextSelectableByMouse)
        content_box.setStyleSheet("""
            QLabel {
                background-color: #13161F;
                border-left: 3px solid #3B82F6;
                padding: 10px 12px;
                color: #E2E8F0;
                font-size: 13px;
                line-height: 1.4;
                border-radius: 4px;
            }
        """)
        layout.addWidget(content_box)

        # 3. 底部操作按钮栏
        actions = QHBoxLayout()
        actions.addStretch()

        btn_jump = QPushButton("🚀 定位到此页")
        btn_jump.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        btn_jump.clicked.connect(self.on_jump_clicked)
        actions.addWidget(btn_jump)

        btn_copy = QPushButton("📋 复制")
        btn_copy.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        btn_copy.clicked.connect(self.on_copy_clicked)
        actions.addWidget(btn_copy)

        btn_del = QPushButton("🗑️ 删除")
        btn_del.setStyleSheet("padding: 4px 10px; font-size: 11px; background-color: #3F1D1D; color: #FCA5A5; border: 1px solid #7F1D1D;")
        btn_del.clicked.connect(self.on_delete_clicked)
        actions.addWidget(btn_del)

        layout.addLayout(actions)

    def on_jump_clicked(self):
        self.jump_requested.emit(self.note["book_id"], self.note["page_num"])

    def on_copy_clicked(self):
        QApplication.clipboard().setText(self.note.get("content", ""))
        QMessageBox.information(self, "提示", "笔记内容已复制到剪贴板！")

    def on_delete_clicked(self):
        if QMessageBox.question(self, "确认删除", "确定要删除这条笔记吗？") == QMessageBox.Yes:
            if api_client.delete_note(self.note["id"]):
                self.deleted.emit(self.note["id"])


class NotesDialog(QDialog):
    jump_to_page_signal = Signal(int)  # 仅针对当前书籍快速跳转页码

    def __init__(self, current_book_id: Optional[int] = None, current_book_title: str = "", parent=None):
        super().__init__(parent)
        self.current_book_id = current_book_id
        self.current_book_title = current_book_title
        self.all_notes: List[Dict[str, Any]] = []

        self.setWindowTitle("📝 我的读书笔记")
        self.resize(780, 580)
        self.init_ui()
        self.refresh_notes()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # 1. 顶部操作栏
        top_bar = QHBoxLayout()

        self.scope_combo = QComboBox()
        self.scope_combo.setStyleSheet("""
            QComboBox {
                background-color: #1E2330;
                border: 1px solid #333B50;
                border-radius: 6px;
                padding: 5px 12px;
                color: #FFFFFF;
                min-width: 130px;
            }
        """)
        self.scope_combo.addItem("📖 当前书籍笔记", "current")
        self.scope_combo.addItem("📚 全部图书笔记", "all")
        self.scope_combo.currentIndexChanged.connect(self.refresh_notes)
        top_bar.addWidget(self.scope_combo)

        top_bar.addSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索笔记关键词...")
        self.search_input.textChanged.connect(self.filter_notes)
        top_bar.addWidget(self.search_input)

        self.count_label = QLabel("共 0 条笔记")
        self.count_label.setStyleSheet("color: #94A3B8; font-size: 12px; margin-left: 10px;")
        top_bar.addWidget(self.count_label)

        layout.addLayout(top_bar)

        # 2. 笔记卡片滚动列表
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: transparent; border: none;")

        self.notes_container = QWidget()
        self.notes_layout = QVBoxLayout(self.notes_container)
        self.notes_layout.setAlignment(Qt.AlignTop)
        self.notes_layout.setSpacing(10)
        self.notes_layout.setContentsMargins(0, 4, 8, 4)

        self.scroll_area.setWidget(self.notes_container)
        layout.addWidget(self.scroll_area)

    def refresh_notes(self):
        scope = self.scope_combo.currentData()
        if scope == "current" and self.current_book_id:
            self.all_notes = api_client.get_notes(self.current_book_id)
        else:
            self.all_notes = api_client.get_notes()
        self.render_notes(self.all_notes)

    def render_notes(self, notes_to_display: List[Dict[str, Any]]):
        while self.notes_layout.count():
            item = self.notes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.count_label.setText(f"共 {len(notes_to_display)} 条笔记")

        if not notes_to_display:
            empty_lbl = QLabel("暂无笔记。\n在阅读时使用鼠标选中文本，点击弹出的【记笔记】即可保存！")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #64748B; font-size: 14px; padding: 60px;")
            self.notes_layout.addWidget(empty_lbl)
            return

        for note in notes_to_display:
            card = NoteCard(note)
            card.jump_requested.connect(self.on_jump_to_note)
            card.deleted.connect(lambda _: self.refresh_notes())
            self.notes_layout.addWidget(card)

    def filter_notes(self, text: str):
        query = text.strip().lower()
        if not query:
            self.render_notes(self.all_notes)
            return
        filtered = [
            n for n in self.all_notes
            if query in n.get("content", "").lower() or query in n.get("book_title", "").lower()
        ]
        self.render_notes(filtered)

    def on_jump_to_note(self, book_id: int, page_num: int):
        if self.current_book_id and book_id == self.current_book_id:
            self.jump_to_page_signal.emit(page_num)
            self.accept()
        else:
            QMessageBox.information(self, "提示", f"该笔记来自其他书籍（P.{page_num}），请先在书架打开对应书籍。")
