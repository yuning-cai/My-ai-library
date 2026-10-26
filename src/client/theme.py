DARK_THEME = """
/* 全局基础设置 */
QWidget {
    background-color: #12141A;
    color: #E2E8F0;
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: 13px;
    selection-background-color: #3B82F6;
    selection-color: #FFFFFF;
}

/* 主窗口与主分割条 */
QMainWindow {
    background-color: #0F1117;
}

QSplitter::handle {
    background-color: #1E2330;
    width: 2px;
    height: 2px;
}
QSplitter::handle:hover {
    background-color: #3B82F6;
}

/* 顶部与底栏容器 */
QFrame#topBar {
    background-color: #181B24;
    border-bottom: 1px solid #232838;
    padding: 6px 12px;
}

QFrame#toolbar {
    background-color: #181B24;
    border-bottom: 1px solid #232838;
    padding: 1px 8px;
    max-height: 38px;
    min-height: 38px;
}

/* 阅读器工具栏紧凑元素 */
QFrame#toolbar QPushButton {
    padding: 3px 10px;
    font-size: 12px;
    min-height: 26px;
    max-height: 26px;
    border-radius: 4px;
}

QFrame#toolbar QLineEdit {
    padding: 2px 4px;
    font-size: 12px;
    min-height: 24px;
    max-height: 24px;
    border-radius: 4px;
}

/* 按钮样式 */
QPushButton {
    background-color: #242938;
    color: #F1F5F9;
    border: 1px solid #333B50;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #2F364A;
    border-color: #475569;
}
QPushButton:pressed {
    background-color: #1E2330;
}
QPushButton:checked {
    background-color: #1E3A8A;
    border-color: #3B82F6;
    color: #93C5FD;
}
QPushButton#primaryBtn {
    background-color: #2563EB;
    border: 1px solid #3B82F6;
    color: #FFFFFF;
    font-weight: 600;
}
QPushButton#primaryBtn:hover {
    background-color: #1D4ED8;
    border-color: #60A5FA;
}
QPushButton#primaryBtn:pressed {
    background-color: #1E40AF;
}
QPushButton#dangerBtn {
    background-color: #7F1D1D;
    border: 1px solid #991B1B;
    color: #FEE2E2;
}
QPushButton#dangerBtn:hover {
    background-color: #991B1B;
}

/* 输入框 */
QLineEdit {
    background-color: #1A1D27;
    border: 1px solid #2C3345;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F8FAFC;
}
QLineEdit:focus {
    border: 1px solid #3B82F6;
    background-color: #1E2230;
}

/* 滚动区域与滚动条 */
QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background: #141720;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #2E364A;
    min-height: 24px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: #141720;
    height: 10px;
    margin: 0px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #2E364A;
    min-width: 24px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #475569;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* 树形组件 (目录大纲) */
QTreeWidget {
    background-color: #161922;
    border: 1px solid #232838;
    border-radius: 8px;
    padding: 6px;
    outline: none;
}
QTreeWidget::item {
    padding: 6px 4px;
    border-radius: 4px;
    color: #CBD5E1;
}
QTreeWidget::item:hover {
    background-color: #212636;
    color: #FFFFFF;
}
QTreeWidget::item:selected {
    background-color: #1E3A8A;
    color: #93C5FD;
    font-weight: bold;
}

/* 进度条 */
QProgressBar {
    border: none;
    background-color: #1E2330;
    border-radius: 3px;
    text-align: center;
    color: transparent;
    height: 6px;
}
QProgressBar::chunk {
    background-color: #3B82F6;
    border-radius: 3px;
}

/* 标签与徽章 */
QLabel#titleLabel {
    font-size: 18px;
    font-weight: 700;
    color: #F8FAFC;
}
QLabel#subtitleLabel {
    font-size: 12px;
    color: #64748B;
}
QLabel#badge {
    background-color: #1E293B;
    color: #38BDF8;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
}

/* 卡片容器 */
QFrame#card {
    background-color: #1A1E29;
    border: 1px solid #262D3D;
    border-radius: 10px;
}
QFrame#card:hover {
    border-color: #3B82F6;
    background-color: #1F2433;
}

/* 菜单 */
QMenu {
    background-color: #1E2230;
    border: 1px solid #333B50;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 20px;
    border-radius: 4px;
    color: #E2E8F0;
}
QMenu::item:selected {
    background-color: #2563EB;
    color: #FFFFFF;
}
"""
