from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QMainWindow, QStackedWidget, QStatusBar, QLabel, QApplication
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QIcon

from src.client.widgets.library_view import LibraryView
from src.client.widgets.pdf_viewer import PdfViewer
from src.config import API_BASE_URL


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("私人图书馆 - PDF E-Book Reader")
        self.resize(1280, 820)
        self.setMinimumSize(900, 600)
        self._drag_pos: Optional[QPoint] = None

        self.init_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """确保在多显示器/主屏幕切换环境下，窗口精确居中在当前主屏幕工作区内"""
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            w = min(self.width(), avail.width() - 40)
            h = min(self.height(), avail.height() - 40)
            self.resize(w, h)
            x = avail.x() + (avail.width() - w) // 2
            y = avail.y() + (avail.height() - h) // 2
            self.move(x, y)

    def init_ui(self):
        # 1. 堆栈视口
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # 视图 0: 书架
        self.library_view = LibraryView()
        self.library_view.open_book_requested.connect(self.open_book)
        self.library_view.status_message.connect(self.show_status_message)
        self.stacked_widget.addWidget(self.library_view)

        # 视图 1: 阅读器
        self.pdf_viewer = PdfViewer()
        self.pdf_viewer.back_to_library.connect(self.switch_to_library)
        self.stacked_widget.addWidget(self.pdf_viewer)

        # 2. 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_msg_label = QLabel("🚀 系统就绪")
        self.status_msg_label.setStyleSheet("color: #94A3B8; font-size: 12px; padding-left: 8px;")
        self.status_bar.addWidget(self.status_msg_label)

        self.status_api_badge = QLabel(f"⚡ FastAPI: {API_BASE_URL}")
        self.status_api_badge.setStyleSheet("color: #38BDF8; font-size: 11px; padding-right: 12px;")
        self.status_bar.addPermanentWidget(self.status_api_badge)

    def open_book(self, book_data: Dict[str, Any]):
        self.status_msg_label.setText(f"📖 正在打开: {book_data.get('title')}")
        self.pdf_viewer.load_book(book_data)
        self.stacked_widget.setCurrentIndex(1)

    def switch_to_library(self):
        self.stacked_widget.setCurrentIndex(0)
        self.library_view.refresh_books()
        self.status_msg_label.setText("📚 已返回书架")

    def show_status_message(self, message: str):
        self.status_msg_label.setText(message)

    def mousePressEvent(self, event):
        # 允许在多屏/扩展屏环境下通过顶部空白区域自由拖拽移动窗口
        if event.button() == Qt.LeftButton and event.position().y() < 50:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos and (event.buttons() & Qt.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def closeEvent(self, event):
        # 如果当前在阅读器视图，保存阅读进度
        if self.stacked_widget.currentIndex() == 1:
            self.pdf_viewer.sync_progress_to_server()
        super().closeEvent(event)
