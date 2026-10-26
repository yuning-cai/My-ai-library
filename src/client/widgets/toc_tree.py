from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QLineEdit
)
from PySide6.QtCore import Qt, Signal


class TocTreeWidget(QWidget):
    page_selected = Signal(int)  # 选中页码 (从 1 开始)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(220)
        self.setMaximumWidth(360)
        self.items_by_page = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 标题
        title = QLabel("📑 目录大纲")
        title.setStyleSheet("font-weight: bold; color: #94A3B8; font-size: 12px;")
        layout.addWidget(title)

        # 过滤搜索框
        self.filter_box = QLineEdit()
        self.filter_box.setPlaceholderText("🔍 快速检索章节...")
        self.filter_box.textChanged.connect(self.filter_items)
        layout.addWidget(self.filter_box)

        # 目录树控件
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.tree)

    def load_toc(self, toc_items: List[Dict[str, Any]]):
        self.tree.clear()
        self.items_by_page = []
        if not toc_items:
            empty_item = QTreeWidgetItem(["(该 PDF 暂无原生目录大纲)"])
            empty_item.setFlags(Qt.NoItemFlags)
            self.tree.addTopLevelItem(empty_item)
            return

        # 根据 level 构建层级树
        level_stack = [(0, self.tree)]  # (level, parent_widget_or_item)

        for item in toc_items:
            level = item.get("level", 1)
            title = item.get("title", "未命名章节")
            page = item.get("page", 1)

            tree_item = QTreeWidgetItem([f"{title}  (P.{page})"])
            tree_item.setData(0, Qt.UserRole, page)
            self.items_by_page.append((int(page), tree_item))

            # 寻找合适的父节点
            while level_stack and level_stack[-1][0] >= level:
                level_stack.pop()

            parent = level_stack[-1][1]
            if isinstance(parent, QTreeWidget):
                parent.addTopLevelItem(tree_item)
            else:
                parent.addChild(tree_item)

            level_stack.append((level, tree_item))

        self.tree.expandAll()

    def select_page(self, page_num: int):
        """精准定位并高亮匹配当前阅读页码的章节目录"""
        if not self.items_by_page:
            return

        # 找到小于等于当前页的最大章节项
        best_item = None
        best_page = -1

        for page, item in self.items_by_page:
            if page <= page_num:
                if page >= best_page:
                    best_page = page
                    best_item = item

        if not best_item and self.items_by_page:
            best_item = self.items_by_page[0][1]

        if best_item:
            self.tree.blockSignals(True)
            # 展开其祖先节点确保可见
            parent = best_item.parent()
            while parent:
                parent.setExpanded(True)
                parent = parent.parent()

            self.tree.setCurrentItem(best_item)
            self.tree.scrollToItem(best_item, QTreeWidget.PositionAtCenter)
            self.tree.blockSignals(False)

    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        page = item.data(0, Qt.UserRole)
        if page is not None:
            self.page_selected.emit(int(page))

    def filter_items(self, query: str):
        query = query.strip().lower()
        def _filter(item: QTreeWidgetItem):
            visible = False
            if query in item.text(0).lower():
                visible = True
            for i in range(item.childCount()):
                child_visible = _filter(item.child(i))
                if child_visible:
                    visible = True
            item.setHidden(not visible)
            return visible

        for i in range(self.tree.topLevelItemCount()):
            _filter(self.tree.topLevelItem(i))
