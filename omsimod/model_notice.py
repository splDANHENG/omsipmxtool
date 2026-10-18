# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Require an explicit acknowledgement of the PMX's own embedded comments."""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPlainTextEdit,
                              QDialogButtonBox)


class ModelNotice(QDialog):
    def __init__(self, metadata, parent=None, *, document=None):
        super().__init__(parent)
        self.setWindowTitle('PMX 内嵌说明 · 请阅读后继续')
        if document is not None:
            self.setWindowTitle('omsipmxtool · 首次使用版权说明')
        self.resize(720, 600)
        self.setMinimumSize(480, 360)
        self.read_complete = False
        layout = QVBoxLayout(self)
        title = QLabel('以下内容来自所选 PMX 文件，由模型提供者编写。')
        if document is not None:
            title.setText('首次使用前请阅读以下项目版权与使用说明。')
        title.setWordWrap(True); layout.addWidget(title)
        sections = ['模型名称：' + metadata['name'],
                    '英文名称：' + metadata['english_name']]
        for label, key in [('原文说明', 'comment'), ('英文说明', 'english_comment')]:
            sections.append(label + '\n' + (metadata[key] or '（该字段为空）'))
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setPlainText('\n\n'.join(sections))
        if document is not None:
            self.text.setPlainText(document)
        layout.addWidget(self.text, 1)
        note = QLabel('请滚动至末尾后点击继续。阅读说明不代表已获得模型使用授权。')
        note.setWordWrap(True); layout.addWidget(note)
        buttons = QDialogButtonBox()
        self.proceed = buttons.addButton('继续', QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton('退出软件' if document is not None else '取消导入', QDialogButtonBox.ButtonRole.RejectRole)
        self.proceed.setEnabled(False)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.text.verticalScrollBar().valueChanged.connect(self.check_end)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.check_end)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self.check_end)

    def check_end(self, *_):
        bar = self.text.verticalScrollBar()
        if self.isVisible() and bar.value() >= bar.maximum():
            self.read_complete = True
            self.proceed.setEnabled(True)

    def accept(self):
        if self.read_complete:
            super().accept()
