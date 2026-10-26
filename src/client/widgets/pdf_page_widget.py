from typing import Optional
import pymupdf
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QPainter, QPixmap, QColor, QPen, QMouseEvent


class PdfPageWidget(QWidget):
    # (page_idx, selected_text, global_mouse_pos)
    text_selected = Signal(int, str, QPoint)
    selection_cleared = Signal()

    def __init__(self, page_idx: int, parent=None):
        super().__init__(parent)
        self.page_idx = page_idx
        self.pixmap: Optional[QPixmap] = None
        self.zoom_factor: float = 1.0
        self.doc: Optional[pymupdf.Document] = None

        self.is_dragging: bool = False
        self.start_pos: QPoint = QPoint()
        self.current_pos: QPoint = QPoint()
        self.selection_rect: QRect = QRect()

        self.setMouseTracking(False)
        self.setCursor(Qt.ArrowCursor)  # 平时默认光标为标准箭头

    def set_content(self, pixmap: Optional[QPixmap], doc: pymupdf.Document, zoom: float):
        self.pixmap = pixmap
        self.doc = doc
        self.zoom_factor = zoom
        self.update()

    def clear_selection(self):
        self.selection_rect = QRect()
        self.is_dragging = False
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # 1. 绘制底层页面像素，精确无损填充
        if self.pixmap and not self.pixmap.isNull():
            painter.drawPixmap(self.rect(), self.pixmap)
        else:
            painter.fillRect(self.rect(), QColor("#161822"))

        # 2. 绘制半透明选区高亮框
        if not self.selection_rect.isNull() and self.selection_rect.isValid():
            painter.setPen(QPen(QColor(59, 130, 246, 220), 1))
            painter.setBrush(QColor(59, 130, 246, 70))
            painter.drawRect(self.selection_rect)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.setCursor(Qt.IBeamCursor)  # 按住开始划词时才切换为文本编辑光标
            self.start_pos = event.pos()
            self.current_pos = event.pos()
            self.selection_rect = QRect()
            self.selection_cleared.emit()
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_dragging and (event.buttons() & Qt.LeftButton):
            self.current_pos = event.pos()
            self.selection_rect = QRect(self.start_pos, self.current_pos).normalized()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.setCursor(Qt.ArrowCursor)  # 松开后立即恢复为正常箭头光标
            rect = self.selection_rect

            # 选区大于阈值时提取文本
            if rect.width() >= 6 and rect.height() >= 6 and self.doc and (0 <= self.page_idx < len(self.doc)):
                page = self.doc[self.page_idx]
                zoom = max(0.1, self.zoom_factor)
                pdf_rect = pymupdf.Rect(
                    rect.left() / zoom,
                    rect.top() / zoom,
                    rect.right() / zoom,
                    rect.bottom() / zoom
                )
                text = page.get_text("text", clip=pdf_rect).strip()
                if text:
                    self.text_selected.emit(self.page_idx, text, event.globalPosition().toPoint())
                else:
                    self.clear_selection()
            else:
                self.clear_selection()
        super().mouseReleaseEvent(event)
