# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Visual editor for exact-name rig overrides."""
import json
from collections import Counter
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QFileDialog, QScrollArea, QWidget, QFormLayout,
    QSplitter, QCheckBox)

from .rig import identify, identify_role
from .model_preview import ModelPreview

ROLE_LABELS = {
    'hips': '骨盆 / 下半身', 'torso': '躯干 / 上半身',
    'head': '头部', 'neck': '颈部',
    'left_thigh': '左大腿', 'right_thigh': '右大腿',
    'left_shin': '左膝 / 小腿', 'right_shin': '右膝 / 小腿',
    'left_arm': '左上臂', 'right_arm': '右上臂',
    'left_elbow': '左肘 / 前臂', 'right_elbow': '右肘 / 前臂',
    'left_hand': '左手腕', 'right_hand': '右手腕',
}


class BoneComboBox(QComboBox):
    def wheelEvent(self, event):
        # Let the surrounding scroll area scroll without changing the mapping.
        event.ignore()


class MappingEditor(QDialog):
    def __init__(self, model, overrides=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.result_mapping = None
        self.setWindowTitle('骨骼映射 · ' + model.name)
        self.resize(1180, 800)
        layout = QVBoxLayout(self)
        note = QLabel('默认自动识别；需要调整时，在下拉框中选择骨骼。可输入名称搜索。\n'
                      '“应用”直接用于本次模型转换；“保存 JSON”可供下次加载。')
        note.setWordWrap(True); layout.addWidget(note)
        editor_note = QLabel('目前本工具导出的 OpenOMSI 模型仅支持右侧列出的骨骼绑定项。'
                             '如需手动调整，请先选择“映射目标”，再点击左侧模型中的骨骼，'
                             '并点击“将选中骨骼映射到当前关节”；也可直接在右侧下拉框中选择骨骼。'
                             '调整完成后，点击“应用”。')
        editor_note.setWordWrap(True)
        layout.addWidget(editor_note)
        split = QSplitter(Qt.Orientation.Horizontal); layout.addWidget(split, 1)
        left = QWidget(); left_layout = QVBoxLayout(left); left_layout.setContentsMargins(0, 0, 8, 0)
        split.addWidget(left)
        self.preview = ModelPreview(model); left_layout.addWidget(self.preview, 1)
        hint = QLabel('左键拖动旋转 · 滚轮缩放 · 右键拖动平移\n'
                      '点击骨骼圆点选中；连线表示父子关系。黄色为选中，橙色为 D 腿骨。')
        hint.setWordWrap(True); left_layout.addWidget(hint)
        view_actions = QHBoxLayout(); left_layout.addLayout(view_actions)
        mesh = QCheckBox('显示模型'); mesh.setChecked(True)
        mesh.toggled.connect(self.preview.set_mesh_visible); view_actions.addWidget(mesh)
        reset = QPushButton('恢复正面'); reset.setAutoDefault(False)
        reset.clicked.connect(self.preview.reset_view); view_actions.addWidget(reset)
        self.target = BoneComboBox()
        for role, label in ROLE_LABELS.items(): self.target.addItem('映射目标：' + label, role)
        left_layout.addWidget(self.target)
        self.candidates = BoneComboBox(); left_layout.addWidget(self.candidates)
        self.selection_note = QLabel('先选择目标关节，再点击模型上的骨骼。')
        self.selection_note.setWordWrap(True); left_layout.addWidget(self.selection_note)
        self.assign_button = QPushButton('将选中骨骼映射到当前关节')
        self.assign_button.setAutoDefault(False); self.assign_button.setEnabled(False)
        self.assign_button.clicked.connect(self.assign_selected); left_layout.addWidget(self.assign_button)
        self.preview.bonesPicked.connect(self.picked_bones)
        self.candidates.currentIndexChanged.connect(self.candidate_changed)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget(); content.setObjectName('root'); form = QFormLayout(content)
        scroll.setWidget(content); split.addWidget(scroll)
        split.setChildrenCollapsible(False); split.setSizes([560, 540])
        self.combos = {}
        name_counts = Counter(name for bone in model.bones for name in {bone.name, bone.english})
        for role, label in ROLE_LABELS.items():
            combo = BoneComboBox(); combo.setEditable(True)
            combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            try:
                index = identify_role(model, role, {})
                automatic = '自动识别 → ' + model.bones[index].name
            except ValueError:
                automatic = '自动识别（未能唯一匹配，请选择）'
            combo.addItem(automatic, None)
            for index, bone in enumerate(model.bones):
                # Exact native names are preferred; English can disambiguate
                # duplicate native names when the file provides a unique alias.
                name = bone.name
                for candidate in (bone.name, bone.english):
                    if candidate and name_counts[candidate] == 1:
                        name = candidate
                        break
                display = f'{index}: {bone.name}'
                if bone.english:
                    display += f' / {bone.english}'
                combo.addItem(display, name)
            combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
            combo.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            combo.setMinimumWidth(230)
            combo.setToolTip(role)
            self.combos[role] = combo
            role_button = QPushButton(label); role_button.setAutoDefault(False)
            role_button.setToolTip('选择映射目标并高亮对应骨骼')
            role_button.clicked.connect(lambda checked=False, r=role: self.show_role(r))
            form.addRow(role_button, combo)
            combo.currentIndexChanged.connect(lambda index, r=role: self.show_role(r))
        self.message = QLabel(); self.message.setWordWrap(True); layout.addWidget(self.message)
        buttons = QHBoxLayout(); layout.addLayout(buttons)
        for text, callback in [('加载 JSON', self.load_file), ('保存 JSON', self.save_file),
                               ('全部恢复自动', lambda: self.set_mapping({})),
                               ('取消', self.reject), ('应用', self.apply)]:
            button = QPushButton(text); button.clicked.connect(callback); buttons.addWidget(button)
            button.setAutoDefault(False)
            if text == '应用': button.setObjectName('primary')
        self.set_mapping(overrides or {})
        self.target.currentIndexChanged.connect(lambda: self.show_role(self.target.currentData()))
        self.show_role('hips')

    def show_role(self, role):
        self.target.blockSignals(True)
        self.target.setCurrentIndex(self.target.findData(role))
        self.target.blockSignals(False)
        combo = self.combos[role]
        try:
            overrides = {role: combo.currentData()} if combo.currentData() is not None else {}
            index = identify_role(self.model, role, overrides)
        except ValueError:
            self.picked_bones([])
            return
        self.picked_bones([index])

    def picked_bones(self, indices):
        self.candidates.blockSignals(True)
        self.candidates.clear()
        for index in indices:
            bone = self.model.bones[index]
            self.candidates.addItem(f'#{index} {bone.name} / {bone.english}', index)
        self.candidates.blockSignals(False)
        self.candidate_changed()

    def candidate_changed(self, *_):
        index = self.candidates.currentData()
        self.preview.select_bone(index)
        self.assign_button.setEnabled(index is not None)
        if index is None:
            self.selection_note.setText('未选中骨骼，请点击圆点或从右侧下拉框选择。')
            return
        bone = self.model.bones[index]
        x, y, z = bone.position
        extra = f'此处有 {self.candidates.count()} 个候选，可在上方切换。\n' if self.candidates.count() > 1 else ''
        self.selection_note.setText(extra + f'选中：{bone.name}  ·  位置 ({x:.3f}, {y:.3f}, {z:.3f})')

    def assign_selected(self):
        index = self.candidates.currentData()
        if index is None: return
        role = self.target.currentData()
        combo = self.combos[role]
        name = combo.itemData(index + 1)
        try:
            resolved = identify_role(self.model, role, {role: name})
            if resolved != index:
                raise ValueError('骨骼名称不能唯一标识所选骨骼。')
        except ValueError as exc:
            self.message.setText('无法映射：' + str(exc)); return
        combo.setCurrentIndex(index + 1)
        self.message.setText(f'已设置 {ROLE_LABELS[role]} → {self.model.bones[index].name}；点击“应用”用于转换。')

    def set_mapping(self, mapping):
        if not isinstance(mapping, dict) or any(
                role not in self.combos or not isinstance(name, str)
                for role, name in mapping.items()):
            raise ValueError('映射必须是关节名称到骨骼名称的 JSON 对象。')
        for role, combo in self.combos.items():
            # Remove unresolved entries from a previously loaded file.
            while combo.count() > len(self.model.bones) + 1:
                combo.removeItem(combo.count() - 1)
            index = combo.findData(mapping[role]) if role in mapping else 0
            if index < 0:
                combo.addItem('待确认：' + mapping[role], mapping[role])
                index = combo.count() - 1
            combo.blockSignals(True)
            combo.setCurrentIndex(index)
            combo.blockSignals(False)
        self.message.setText('未能匹配的映射会保留为“待确认”，请重新选择后应用。')
        self.show_role(self.target.currentData())

    def mapping(self):
        result = {}
        for role, combo in self.combos.items():
            if combo.currentText() != combo.itemText(combo.currentIndex()):
                raise ValueError(f'{ROLE_LABELS[role]}：请从下拉列表选择骨骼。')
            if combo.currentData() is not None:
                result[role] = combo.currentData()
        identify(self.model, result)
        return result

    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, '加载骨骼映射', '', 'JSON (*.json)')
        if not path: return
        try:
            self.set_mapping(json.loads(Path(path).read_text(encoding='utf-8-sig')))
        except (ValueError, OSError) as exc:
            self.message.setText('加载失败：' + str(exc))

    def save_file(self):
        try:
            mapping = self.mapping()
            path, _ = QFileDialog.getSaveFileName(self, '保存骨骼映射', 'bone-mapping.json', 'JSON (*.json)')
            if not path: return
            Path(path).write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf-8')
            self.message.setText('已保存：' + path)
        except (ValueError, OSError) as exc:
            self.message.setText('保存失败：' + str(exc))

    def apply(self):
        try:
            self.result_mapping = self.mapping()
        except ValueError as exc:
            self.message.setText('请修正映射：' + str(exc))
            return
        self.accept()
