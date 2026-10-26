from pathlib import Path
from typing import Dict, Any, Optional, List
import pymupdf
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QSplitter, QFrame, QMessageBox,
    QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint, QEvent
from PySide6.QtGui import QPixmap, QImage, QKeyEvent, QWheelEvent, QFont

from src.client.widgets.toc_tree import TocTreeWidget
from src.client.widgets.pdf_page_widget import PdfPageWidget
from src.client.widgets.selection_popup import SelectionPopup
from src.client.widgets.notes_dialog import NotesDialog
from src.client.api_client import api_client


class PdfViewer(QWidget):
    back_to_library = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc: Optional[pymupdf.Document] = None
        self.book_data: Optional[Dict[str, Any]] = None
        self.current_page_idx: int = 0
        self.total_pages: int = 0
        self.zoom_factor: float = 1.25
        self.dark_mode_enabled: bool = False
        self.is_initializing: bool = False  # 打开书籍定位期间防止误覆盖进度
        
        # 连续滚动页面组件与渲染缓存
        self.page_widgets: List[PdfPageWidget] = []
        self.rendered_cache: Dict[int, bool] = {}
        self.current_selected_page: int = 1
        self.is_cursor_hidden: bool = False  # 按上下键时隐藏光标标志

        self.save_progress_timer = QTimer(self)
        self.save_progress_timer.setInterval(800)
        self.save_progress_timer.setSingleShot(True)
        self.save_progress_timer.timeout.connect(self.sync_progress_to_server)

        self.init_ui()

        # 浮动划词小弹窗
        self.selection_popup = SelectionPopup(self)
        self.selection_popup.save_note_requested.connect(self.save_selected_note)
        self.selection_popup.copy_requested.connect(lambda _: self.clear_all_selections())

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. 顶部主工具栏 (紧凑型设计)
        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        toolbar.setFixedHeight(38)
        tool_layout = QHBoxLayout(toolbar)
        tool_layout.setContentsMargins(10, 2, 10, 2)
        tool_layout.setSpacing(8)

        # 返回书架
        self.btn_back = QPushButton("← 返回书架")
        self.btn_back.clicked.connect(self.on_back_clicked)
        tool_layout.addWidget(self.btn_back)

        # 书名展示
        self.lbl_title = QLabel("正在加载...")
        self.lbl_title.setStyleSheet("font-weight: bold; color: #F8FAFC; font-size: 13px;")
        self.lbl_title.setMaximumWidth(280)
        tool_layout.addWidget(self.lbl_title)

        tool_layout.addSpacing(15)

        # 目录面板展开/折叠 (默认隐藏，点击弹出)
        self.btn_toggle_toc = QPushButton("📑 目录")
        self.btn_toggle_toc.setCheckable(True)
        self.btn_toggle_toc.setChecked(False)
        self.btn_toggle_toc.clicked.connect(self.toggle_toc)
        tool_layout.addWidget(self.btn_toggle_toc)

        tool_layout.addStretch()

        # 翻页控制
        self.btn_prev = QPushButton("◀ 上一页")
        self.btn_prev.clicked.connect(self.prev_page)
        tool_layout.addWidget(self.btn_prev)

        self.page_input = QLineEdit("1")
        self.page_input.setFixedWidth(50)
        self.page_input.setAlignment(Qt.AlignCenter)
        self.page_input.returnPressed.connect(self.jump_to_input_page)
        tool_layout.addWidget(self.page_input)

        self.lbl_page_count = QLabel("/ 0 页")
        self.lbl_page_count.setStyleSheet("color: #94A3B8;")
        tool_layout.addWidget(self.lbl_page_count)

        self.btn_next = QPushButton("下一页 ▶")
        self.btn_next.clicked.connect(self.next_page)
        tool_layout.addWidget(self.btn_next)

        tool_layout.addSpacing(15)

        # 缩放控制
        self.btn_zoom_out = QPushButton("－")
        self.btn_zoom_out.setFixedWidth(32)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        tool_layout.addWidget(self.btn_zoom_out)

        self.lbl_zoom = QLabel("125%")
        self.lbl_zoom.setStyleSheet("color: #94A3B8; font-size: 12px;")
        tool_layout.addWidget(self.lbl_zoom)

        self.btn_zoom_in = QPushButton("＋")
        self.btn_zoom_in.setFixedWidth(32)
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        tool_layout.addWidget(self.btn_zoom_in)

        self.btn_fit_width = QPushButton("适应宽度")
        self.btn_fit_width.clicked.connect(self.fit_width)
        tool_layout.addWidget(self.btn_fit_width)

        tool_layout.addSpacing(10)

        # 深色/浅色模式切换
        self.btn_dark_mode = QPushButton("🌙 深色模式")
        self.btn_dark_mode.setCheckable(True)
        self.btn_dark_mode.setChecked(False)
        self.btn_dark_mode.clicked.connect(self.toggle_dark_mode)
        tool_layout.addWidget(self.btn_dark_mode)

        tool_layout.addSpacing(6)

        # 读书笔记独立窗口
        self.btn_notes = QPushButton("📝 我的笔记")
        self.btn_notes.clicked.connect(self.open_notes_dialog)
        tool_layout.addWidget(self.btn_notes)

        main_layout.addWidget(toolbar)

        # 2. 中间可拖拽主视图 (QSplitter)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(4)

        # 2.1 左侧：目录大纲树 (默认隐藏，按需点击呼出)
        self.toc_widget = TocTreeWidget()
        self.toc_widget.page_selected.connect(self.go_to_page)
        self.toc_widget.setVisible(False)
        self.splitter.addWidget(self.toc_widget)

        # 2.2 右侧：连续滚动 PDF 视口
        self.scroll_area = QScrollArea()
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #0B0D13; border: none;")

        self.pages_container = QWidget()
        self.pages_container.setStyleSheet("background-color: transparent;")
        self.pages_layout = QVBoxLayout(self.pages_container)
        self.pages_layout.setAlignment(Qt.AlignCenter)
        self.pages_layout.setContentsMargins(16, 16, 16, 16)
        self.pages_layout.setSpacing(16)

        self.scroll_area.setWidget(self.pages_container)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self.on_scroll)
        self.scroll_area.installEventFilter(self)
        self.scroll_area.viewport().installEventFilter(self)
        self.splitter.addWidget(self.scroll_area)

        # 初始只让阅读区占满视口
        self.splitter.setSizes([0, 1200])
        main_layout.addWidget(self.splitter)

    def load_book(self, book_data: Dict[str, Any]):
        """打开并加载书籍，初始化连续滚动容器"""
        if self.doc:
            self.doc.close()
            self.doc = None

        self.is_initializing = True
        self.book_data = book_data
        pdf_path = book_data.get("file_path", "")
        if not Path(pdf_path).exists():
            QMessageBox.critical(self, "错误", f"找不到本地 PDF 文件:\n{pdf_path}")
            self.back_to_library.emit()
            return

        try:
            self.doc = pymupdf.open(pdf_path)
            self.total_pages = len(self.doc)
            self.lbl_title.setText(book_data.get("title", "电子书阅读"))
            self.lbl_title.setToolTip(book_data.get("title", ""))
            self.lbl_page_count.setText(f"/ {self.total_pages} 页")

            # 加载目录大纲
            toc = book_data.get("toc", [])
            self.toc_widget.load_toc(toc)

            # 恢复上次阅读进度
            last_page = int(book_data.get("current_page", 1))
            self.current_page_idx = max(0, min(last_page - 1, self.total_pages - 1))
            self.page_input.setText(str(self.current_page_idx + 1))

            # 默认收起目录，最大化阅读视野
            self.btn_toggle_toc.setChecked(False)
            self.toc_widget.setVisible(False)
            self.splitter.setSizes([0, 1200])

            # 清理旧的连续页面占位
            while self.pages_layout.count():
                item = self.pages_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.page_widgets.clear()
            self.rendered_cache.clear()

            # 构建连续页面占位控件 (支持划词选中文本)
            for i in range(self.total_pages):
                rect = self.doc[i].rect
                w = int(rect.width * self.zoom_factor)
                h = int(rect.height * self.zoom_factor)
                page_widget = PdfPageWidget(i)
                page_widget.setFixedSize(w, h)
                page_widget.text_selected.connect(self.on_text_selected)
                page_widget.selection_cleared.connect(self.selection_popup.hide)
                self.pages_layout.addWidget(page_widget)
                self.page_widgets.append(page_widget)

            # 延迟执行自适应宽度与定位到上次阅读位置
            QTimer.singleShot(50, lambda: self._init_view_position(last_page))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开 PDF 失败: {e}")
            self.back_to_library.emit()

    def _init_view_position(self, page_num: int):
        self.fit_width()
        self.go_to_page(page_num)
        # 等页面滚动与几何尺寸稳定后，再开启滚动自动保存
        QTimer.singleShot(150, self._finish_initializing)

    def _finish_initializing(self):
        self.is_initializing = False
        self.on_scroll()

    def render_page(self, page_idx: int, page_widget: PdfPageWidget):
        """按需渲染单页像素并缓存 (视网膜级 1:1 超清渲染)"""
        if not self.doc or not (0 <= page_idx < len(self.doc)):
            return

        page = self.doc[page_idx]

        # 核心：获取屏幕硬件物理 DPI 比例 (例如 Windows 125%, 150%, 200%)
        # 必须乘以 dpr 进行物理超分辨率渲染，彻底告别模糊与毛刺
        dpr = self.devicePixelRatioF() if hasattr(self, 'devicePixelRatioF') else self.devicePixelRatio()
        dpr = max(1.0, float(dpr))

        render_scale = self.zoom_factor * dpr
        matrix = pymupdf.Matrix(render_scale, render_scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        # 深色模式：反转颜色（呈现黑色背景白色字）
        if self.dark_mode_enabled:
            pix.invert_irect()

        qimg = QImage(
            pix.samples,
            pix.width,
            pix.height,
            pix.stride,
            QImage.Format_RGB888
        )
        qpixmap = QPixmap.fromImage(qimg)
        qpixmap.setDevicePixelRatio(dpr)
        page_widget.set_content(qpixmap, self.doc, self.zoom_factor)
        self.rendered_cache[page_idx] = True

    def on_scroll(self):
        """当滚动条变动时，实现平滑视口懒加载与进度计算"""
        if not self.doc or not self.page_widgets:
            return

        # 滚动时自动隐藏划词操作弹窗
        if self.selection_popup.isVisible():
            self.selection_popup.hide()

        scrollbar = self.scroll_area.verticalScrollBar()
        viewport_top = scrollbar.value()
        viewport_h = self.scroll_area.viewport().height()
        viewport_bottom = viewport_top + viewport_h
        center_y = viewport_top + viewport_h // 3

        active_idx = self.current_page_idx
        for idx, page_widget in enumerate(self.page_widgets):
            top_y = page_widget.y()
            bottom_y = top_y + page_widget.height()

            # 识别当前正读的页面（位于视口上半部或中心）
            if top_y <= center_y <= bottom_y:
                active_idx = idx

            # 缓冲区懒加载：在视口上下 1.5 倍屏高内预渲染
            is_visible = (bottom_y >= viewport_top - viewport_h * 1.5) and (top_y <= viewport_bottom + viewport_h * 1.5)
            if is_visible:
                if idx not in self.rendered_cache:
                    self.render_page(idx, page_widget)
            else:
                # 滚出视口过远，释放 pixmap 节省内存
                if idx in self.rendered_cache:
                    page_widget.set_content(None, self.doc, self.zoom_factor)
                    del self.rendered_cache[idx]

        if active_idx != self.current_page_idx:
            self.current_page_idx = active_idx
            self.page_input.setText(str(active_idx + 1))
            if not self.is_initializing:
                self.save_progress_timer.start()
            # 目录展开时，实时跟随阅读进度滚动高亮当前章节
            if self.toc_widget.isVisible():
                self.toc_widget.select_page(active_idx + 1)

    def prev_page(self):
        if self.current_page_idx > 0:
            self.go_to_page(self.current_page_idx)

    def next_page(self):
        if self.current_page_idx < self.total_pages - 1:
            self.go_to_page(self.current_page_idx + 2)

    def go_to_page(self, page_num: int):
        """平滑滚动定位到指定页"""
        target_idx = max(0, min(page_num - 1, self.total_pages - 1))
        if 0 <= target_idx < len(self.page_widgets):
            target_lbl = self.page_widgets[target_idx]
            target_y = target_lbl.y()
            if target_y <= 0 and target_idx > 0:
                target_y = 16
                for i in range(target_idx):
                    h = int(self.doc[i].rect.height * self.zoom_factor)
                    target_y += h + 16
            self.scroll_area.verticalScrollBar().setValue(target_y)
            self.current_page_idx = target_idx
            self.page_input.setText(str(target_idx + 1))
            QTimer.singleShot(20, self.on_scroll)

    def jump_to_input_page(self):
        text = self.page_input.text().strip()
        if text.isdigit():
            self.go_to_page(int(text))
        else:
            self.page_input.setText(str(self.current_page_idx + 1))

    def apply_zoom(self):
        """缩放并调整所有连续页面的尺寸，确保视觉锚点精确锁定在当前阅读位置"""
        if not self.doc or not self.page_widgets:
            return

        # 1. 记录缩放前当前正读页及页内相对偏移比率 (保持视口中心不偏移)
        anchor_idx = max(0, min(self.current_page_idx, self.total_pages - 1))
        anchor_widget = self.page_widgets[anchor_idx]
        current_scroll = self.scroll_area.verticalScrollBar().value()
        anchor_old_y = anchor_widget.y()
        if anchor_old_y <= 0 and anchor_idx > 0:
            anchor_old_y = 16
            for i in range(anchor_idx):
                anchor_old_y += self.page_widgets[i].height() + 16

        offset_in_page = max(0, current_scroll - anchor_old_y)
        offset_ratio = offset_in_page / max(1, anchor_widget.height())

        # 2. 清理旧缓存并计算各页新尺寸与锚点新坐标
        self.rendered_cache.clear()
        total_h = 16
        max_w = 0
        new_anchor_y = 16

        for idx, lbl in enumerate(self.page_widgets):
            rect = self.doc[idx].rect
            w = int(rect.width * self.zoom_factor)
            h = int(rect.height * self.zoom_factor)
            lbl.setFixedSize(w, h)
            if idx < anchor_idx:
                new_anchor_y += h + 16
            total_h += h + 16
            if w > max_w:
                max_w = w

        self.pages_container.setMinimumSize(max_w + 32, total_h + 16)
        self.lbl_zoom.setText(f"{int(self.zoom_factor * 100)}%")
        self.pages_container.adjustSize()

        # 3. 核心：重设滚动条位置，使当前阅读位置丝毫不动
        new_anchor_h = self.page_widgets[anchor_idx].height()
        new_scroll_val = new_anchor_y + int(offset_ratio * new_anchor_h)
        self.scroll_area.verticalScrollBar().setValue(new_scroll_val)
        self.current_page_idx = anchor_idx
        self.page_input.setText(str(anchor_idx + 1))

        if not self.is_initializing:
            QTimer.singleShot(20, self.on_scroll)

    def zoom_in(self):
        if self.zoom_factor < 3.5:
            self.zoom_factor += 0.2
            self.apply_zoom()

    def zoom_out(self):
        if self.zoom_factor > 0.6:
            self.zoom_factor -= 0.2
            self.apply_zoom()

    def fit_width(self):
        if not self.doc or not self.page_widgets:
            return
        viewport_width = self.scroll_area.viewport().width()
        if viewport_width < 300:
            viewport_width = max(700, self.width() - 60)
        target_w = max(300, viewport_width - 48)
        first_page_w = self.doc[0].rect.width if len(self.doc) > 0 else 595
        if first_page_w > 0:
            self.zoom_factor = max(0.8, min(3.5, target_w / first_page_w))
            self.apply_zoom()

    def toggle_toc(self):
        visible = self.btn_toggle_toc.isChecked()
        self.toc_widget.setVisible(visible)
        total_w = self.splitter.width() or self.width()
        if visible:
            reader_w = max(400, total_w - 260)
            self.splitter.setSizes([260, reader_w])
            # 呼出目录时，立即自动定位并居中高亮当前阅读位置的章节
            self.toc_widget.select_page(self.current_page_idx + 1)
        else:
            self.splitter.setSizes([0, total_w])

    def toggle_dark_mode(self):
        """切换深色/浅色阅读模式"""
        self.dark_mode_enabled = self.btn_dark_mode.isChecked()
        if self.dark_mode_enabled:
            self.btn_dark_mode.setText("☀️ 浅色模式")
            self.scroll_area.setStyleSheet("background-color: #060709; border: none;")
        else:
            self.btn_dark_mode.setText("🌙 深色模式")
            self.scroll_area.setStyleSheet("background-color: #0B0D13; border: none;")
        # 清空当前渲染缓存，立即重绘当前可见页面
        self.rendered_cache.clear()
        self.on_scroll()

    def clear_all_selections(self):
        """清除所有页面上的划词蓝色高亮框"""
        for w in self.page_widgets:
            w.clear_selection()

    def on_text_selected(self, page_idx: int, text: str, global_pos: QPoint):
        """当用户在任意页面用鼠标选中文本时，在光标旁弹出操作小窗口"""
        # 清除其它页可能残留的选区，确保界面仅保留当前高亮
        for idx, w in enumerate(self.page_widgets):
            if idx != page_idx:
                w.clear_selection()
        self.current_selected_page = page_idx + 1
        self.selection_popup.show_at(global_pos, text)

    def save_selected_note(self, text: str):
        """保存划词文本到个人笔记，并立即让选中的蓝色框自动消失"""
        if self.book_data and text.strip():
            book_id = self.book_data["id"]
            book_title = self.book_data.get("title", "未命名书籍")
            api_client.add_note(book_id, book_title, self.current_selected_page, text.strip())
        # 点击存笔记后，立刻让蓝色选框自动消失
        self.clear_all_selections()

    def open_notes_dialog(self):
        """弹出独立的读书笔记管理窗口"""
        cur_id = self.book_data["id"] if self.book_data else None
        cur_title = self.book_data.get("title", "") if self.book_data else ""
        dialog = NotesDialog(current_book_id=cur_id, current_book_title=cur_title, parent=self)
        dialog.jump_to_page_signal.connect(self.go_to_page)
        dialog.exec()

    def sync_progress_to_server(self):
        if self.book_data:
            book_id = self.book_data["id"]
            cur_page = self.current_page_idx + 1
            api_client.update_progress(book_id, cur_page, self.total_pages)
            self.book_data["current_page"] = cur_page

    def hide_cursor_for_reading(self):
        """按方向键等阅读翻页时，立即隐藏鼠标光标，防止遮挡文字"""
        if not self.is_cursor_hidden:
            QApplication.setOverrideCursor(Qt.BlankCursor)
            self.is_cursor_hidden = True

    def restore_cursor(self):
        """当鼠标晃动或操作时，立即无缝恢复鼠标光标"""
        if self.is_cursor_hidden:
            QApplication.restoreOverrideCursor()
            self.is_cursor_hidden = False

    def eventFilter(self, watched, event):
        # 1. 光标隐藏状态下，只要发生鼠标移动或点击，立刻恢复光标
        if self.is_cursor_hidden and event.type() in (QEvent.MouseMove, QEvent.MouseButtonPress):
            self.restore_cursor()
        # 2. 当按下上下翻页按键时，快速隐藏光标
        elif event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Down, Qt.Key_Up, Qt.Key_PageDown, Qt.Key_PageUp, Qt.Key_Space):
                self.hide_cursor_for_reading()
        return False

    def hideEvent(self, event):
        self.restore_cursor()
        super().hideEvent(event)

    def on_back_clicked(self):
        self.restore_cursor()
        if self.save_progress_timer.isActive():
            self.save_progress_timer.stop()
        self.sync_progress_to_server()
        if self.doc:
            self.doc.close()
            self.doc = None
        self.back_to_library.emit()

    # 快捷键支持
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Left, Qt.Key_PageUp):
            self.prev_page()
        elif event.key() in (Qt.Key_Right, Qt.Key_PageDown, Qt.Key_Space):
            self.next_page()
        elif event.key() == Qt.Key_Home:
            self.go_to_page(1)
        elif event.key() == Qt.Key_End:
            self.go_to_page(self.total_pages)
        elif event.key() == Qt.Key_D:
            self.btn_dark_mode.setChecked(not self.btn_dark_mode.isChecked())
            self.toggle_dark_mode()
        else:
            super().keyPressEvent(event)

    # Ctrl + 滚轮缩放，普通滚轮顺畅连续下滑
    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)
