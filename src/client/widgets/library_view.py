from pathlib import Path
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QGridLayout, QFileDialog, QMessageBox,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QThread
from src.client.widgets.book_card import BookCard
from src.client.widgets.notes_dialog import NotesDialog
from src.client.api_client import api_client


class UploadWorker(QThread):
    finished_signal = Signal(bool, str, dict)  # success, message, book_data

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            res = api_client.upload_book(self.file_path)
            if res:
                self.finished_signal.emit(True, res.get("message", "上传成功"), res.get("book", {}))
            else:
                self.finished_signal.emit(False, "服务端返回异常", {})
        except Exception as e:
            self.finished_signal.emit(False, str(e), {})


class LibraryView(QWidget):
    open_book_requested = Signal(dict)  # book_dict
    status_message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.books: List[Dict[str, Any]] = []
        self.upload_workers: List[UploadWorker] = []
        self.setAcceptDrops(True)  # 支持拖拽上传

        self.init_ui()
        self.refresh_books()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # 1. 顶部操作栏
        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 10)

        # 标题与副标题
        title_box = QVBoxLayout()
        self.title_label = QLabel("📚 我的藏书馆")
        self.title_label.setObjectName("titleLabel")
        self.subtitle_label = QLabel("正在连接本地数据服务...")
        self.subtitle_label.setObjectName("subtitleLabel")
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.subtitle_label)
        top_layout.addLayout(title_box)

        top_layout.addStretch()

        # 搜索过滤框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索藏书名或作者...")
        self.search_input.setFixedWidth(220)
        self.search_input.textChanged.connect(self.filter_books)
        top_layout.addWidget(self.search_input)

        # 刷新按钮
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self.refresh_books)
        top_layout.addWidget(self.refresh_btn)

        # 读书笔记按钮
        self.notes_btn = QPushButton("📝 读书笔记")
        self.notes_btn.clicked.connect(self.open_notes_dialog)
        top_layout.addWidget(self.notes_btn)

        # 导入 PDF 按钮
        self.import_btn = QPushButton("➕ 导入 PDF 电子书")
        self.import_btn.setObjectName("primaryBtn")
        self.import_btn.clicked.connect(self.select_and_upload)
        top_layout.addWidget(self.import_btn)

        main_layout.addWidget(top_bar)

        # 2. 书籍卡片展示滚动区
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.scroll_area.setWidget(self.grid_container)
        main_layout.addWidget(self.scroll_area)

    def refresh_books(self):
        """从 FastAPI 获取书籍列表并刷新界面"""
        self.books = api_client.get_books()
        count = len(self.books)
        self.subtitle_label.setText(f"共收录 {count} 本电子书 · 支持直接拖拽 PDF 文件至此窗口")
        self.render_grid(self.books)

    def render_grid(self, books_to_show: List[Dict[str, Any]]):
        # 清空现有网格
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not books_to_show:
            # 空状态提示
            empty_box = QWidget()
            empty_layout = QVBoxLayout(empty_box)
            empty_layout.setAlignment(Qt.AlignCenter)
            empty_layout.setContentsMargins(40, 60, 40, 60)

            icon = QLabel("📖")
            icon.setStyleSheet("font-size: 54px;")
            icon.setAlignment(Qt.AlignCenter)
            empty_layout.addWidget(icon)

            msg = QLabel("书架暂无书籍，点击右上角【导入 PDF】或将 PDF 直接拖入窗口")
            msg.setStyleSheet("color: #64748B; font-size: 14px; margin-top: 10px;")
            msg.setAlignment(Qt.AlignCenter)
            empty_layout.addWidget(msg)

            empty_btn = QPushButton("➕ 立即导入电子书")
            empty_btn.setObjectName("primaryBtn")
            empty_btn.setFixedSize(160, 36)
            empty_btn.clicked.connect(self.select_and_upload)
            empty_layout.addWidget(empty_btn, alignment=Qt.AlignCenter)

            self.grid_layout.addWidget(empty_box, 0, 0, 1, 4)
            return

        columns = 4  # 每行最多显示 4 本
        for idx, book in enumerate(books_to_show):
            row = idx // columns
            col = idx % columns
            card = BookCard(book)
            card.clicked.connect(self.on_book_card_clicked)
            card.delete_requested.connect(self.on_book_delete_requested)
            self.grid_layout.addWidget(card, row, col)

    def open_notes_dialog(self):
        dialog = NotesDialog(parent=self)
        dialog.exec()

    def filter_books(self, text: str):
        query = text.strip().lower()
        if not query:
            self.render_grid(self.books)
            return
        filtered = [
            b for b in self.books
            if query in b.get("title", "").lower() or query in b.get("author", "").lower()
        ]
        self.render_grid(filtered)

    def select_and_upload(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 PDF 电子书",
            "",
            "PDF 文件 (*.pdf);;所有文件 (*.*)"
        )
        if file_path:
            self.start_upload(file_path)

    def start_upload(self, file_path: str):
        self.status_message.emit(f"正在导入并解析书籍: {Path(file_path).name} ...")
        worker = UploadWorker(file_path)
        worker.finished_signal.connect(self.on_upload_finished)
        self.upload_workers.append(worker)
        worker.start()

    def on_upload_finished(self, success: bool, message: str, book: dict):
        if success:
            self.status_message.emit(f"🎉 导入成功: {book.get('title', '书籍')}")
            self.refresh_books()
        else:
            self.status_message.emit(f"❌ 导入失败: {message}")
            QMessageBox.warning(self, "导入失败", f"无法上传解析该 PDF:\n{message}")

    def on_book_card_clicked(self, book_id: int):
        book = api_client.get_book(book_id)
        if book:
            self.open_book_requested.emit(book)
        else:
            QMessageBox.warning(self, "错误", "无法打开此书籍")

    def on_book_delete_requested(self, book_id: int):
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要将这本电子书从图书馆中删除吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success = api_client.delete_book(book_id)
            if success:
                self.status_message.emit("已成功删除图书")
                self.refresh_books()
            else:
                QMessageBox.warning(self, "删除失败", "删除书籍过程中发生错误")

    # 拖拽处理
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(url.toLocalFile().lower().endswith(".pdf") for url in urls):
                event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        for url in urls:
            path_str = url.toLocalFile()
            if path_str.lower().endswith(".pdf"):
                self.start_upload(path_str)
        event.acceptProposedAction()
