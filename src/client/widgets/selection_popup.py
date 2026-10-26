from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QGraphicsDropShadowEffect, QApplication
)
from PySide6.QtCore import Qt, Signal, QPoint, QTimer
from PySide6.QtGui import QColor, QCursor


class SelectionPopup(QWidget):
    save_note_requested = Signal(str)  # 选中的文本
    copy_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.current_text = ""

        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # 容器背景框
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #1E2330;
                border: 1px solid #3B82F6;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #283042;
                color: #FFFFFF;
                border: 1px solid #434D66;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3B82F6;
                border-color: #60A5FA;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
        """)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        container.setGraphicsEffect(shadow)

        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(6, 4, 6, 4)
        c_layout.setSpacing(6)

        self.btn_note = QPushButton("📝 记笔记")
        self.btn_note.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_note.clicked.connect(self.on_save_clicked)
        c_layout.addWidget(self.btn_note)

        self.btn_copy = QPushButton("📋 复制")
        self.btn_copy.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_copy.clicked.connect(self.on_copy_clicked)
        c_layout.addWidget(self.btn_copy)

        layout.addWidget(container)

    def show_at(self, global_pos: QPoint, text: str):
        self.current_text = text
        self.btn_note.setText("📝 记笔记")
        self.btn_copy.setText("📋 复制")
        self.adjustSize()
        # 弹窗默认显示在鼠标上方偏右，避免遮挡选区
        x = global_pos.x() + 10
        y = max(10, global_pos.y() - self.height() - 10)
        self.move(x, y)
        self.show()

    def on_save_clicked(self):
        self.btn_note.setText("✅ 已记下")
        self.save_note_requested.emit(self.current_text)
        QTimer.singleShot(500, self.hide)

    def on_copy_clicked(self):
        QApplication.clipboard().setText(self.current_text)
        self.btn_copy.setText("✅ 已复制")
        self.copy_requested.emit(self.current_text)
        QTimer.singleShot(400, self.hide)
