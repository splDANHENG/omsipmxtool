# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Cross-platform Qt desktop front end; converters run off the UI thread."""
import json
import sys
from pathlib import Path
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QDoubleSpinBox,
    QPlainTextEdit, QProgressBar, QFrame, QFormLayout, QTabWidget, QCheckBox,
    QScrollArea)
from .pmx import load, read_metadata
from .model_notice import ModelNotice
from .naming import pinyin_name
from .export import convert, character_name
from .ai_help import make_help_button


def pmx_height(model):
    # Conventional MMD scale; PMX has no authoritative real-world height field.
    if not model.vertices:
        raise ValueError('模型没有顶点，无法读取高度。')
    ys = [v.position[1] for v in model.vertices]
    return (max(ys) - min(ys)) * 0.08


def export_destination(root, name):
    folder = Path(root).resolve() / 'omsipmxtool_exports'
    candidate = folder / character_name(name)
    index = 2
    while candidate.exists():
        candidate = folder / f'{character_name(name)}_{index}'
        index += 1
    if not candidate.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('统一导出目录必须位于 OMSI 安装目录内。')
    return candidate


class Events(QObject):
    done = Signal(object)
    failed = Signal(str)


class Work(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.events = Events()

    def run(self):
        try:
            self.events.done.emit(self.function())
        except Exception as exc:
            self.events.failed.emit(str(exc))


def inspect_model(path):
    model = load(path)
    return {'name': model.name, 'estimated_height': pmx_height(model), 'vertices': len(model.vertices),
            'triangles': len(model.indices)//3, 'materials': len(model.materials),
            'bones': [{'name': b.name, 'english': b.english, 'parent': b.parent}
                      for b in model.bones], 'warnings': model.warnings}


def convert_model(source, output, name, height, mapping, *, adapt_thumbs=False):
    overrides = dict(mapping) if isinstance(mapping, dict) else (json.loads(mapping.read_text(encoding='utf-8-sig')) if mapping else {})
    if not isinstance(overrides, dict):
        raise ValueError('骨骼映射必须是 JSON 对象。')
    model = load(source)
    automatic = height is None
    if automatic:
        height = pmx_height(model)
        if not 0.5 <= height <= 3:
            raise ValueError(f'自动估算高度 {height:.3f} m 超出人物范围，请取消自动读取并手动设置模型总高度。')
    report = convert(model, source, output, name, height, overrides, adapt_thumbs=adapt_thumbs)
    report['height_mode'] = 'mmd_bounds_0.08' if automatic else 'manual'
    return report


def convert_and_install(source, output, name, height, mapping, library, game_root, *, adapt_thumbs=False):
    report = convert_model(source, output, name, height, mapping, adapt_thumbs=adapt_thumbs)
    report['installation'] = {'status': 'not_requested'}
    try:
        item = library.add(output/'Humans'/report['character']/'driver.hum')
        report['library_id'] = item['id']
    except Exception as exc:
        report['installation'] = {'status': 'failed', 'error': str(exc)}
        report['warnings'].append('人物包已保留；角色库导入失败：'+str(exc))
    else:
        if game_root is not None:
            try:
                installed = library.install(item, game_root)
                report['installation'] = {'status': 'installed', 'hum': str(installed)}
            except Exception as exc:
                report['installation'] = {'status': 'failed', 'error': str(exc)}
                report['warnings'].append('人物包已保留；自动安装失败，可在角色库中重试应用：'+str(exc))
    from .library import atomic_write
    try:
        atomic_write(output/'conversion-report.json', json.dumps(report, ensure_ascii=False, indent=2).encode('utf-8'))
    except OSError as exc:
        report['warnings'].append('安装结果未能写入转换报告：'+str(exc))
    return report


STYLE = '''
QWidget { font-family: ".AppleSystemUIFont", "Segoe UI", sans-serif; font-size: 13px; color: #dce5f1; }
QMainWindow, QDialog, #root, #manager { background: #101720; }
QFrame#card { background: #182330; border: 1px solid #2a394b; border-radius: 12px; }
QLabel#title { font-size: 29px; font-weight: 700; color: #ffffff; }
QLabel#eyebrow { color: #65d7bd; font-weight: 600; letter-spacing: 2px; }
QLabel#muted { color: #9caec1; }
QLabel#section { font-size: 16px; font-weight: 600; }
QLineEdit, QDoubleSpinBox, QPlainTextEdit { background: #101923; border: 1px solid #35485c; border-radius: 6px; padding: 8px; selection-background-color: #24655e; }
QLineEdit:focus, QDoubleSpinBox:focus { border: 1px solid #65d7bd; }
QPushButton { background: #293c50; border: 1px solid #3b5168; border-radius: 7px; padding: 9px 15px; font-weight: 600; }
QPushButton:hover { background: #354e68; }
QPushButton#primary { background: #65d7bd; color: #102820; border: none; padding: 12px 24px; }
QPushButton#primary:hover { background: #8ae8d3; }
QPushButton:disabled { color: #6a7a8d; background: #202d3b; border-color: #29394b; }
QProgressBar { border: none; background: #293b4e; border-radius: 3px; min-height: 5px; max-height: 5px; }
QProgressBar::chunk { background: #65d7bd; border-radius: 3px; }
QTabWidget::pane { background: #101720; border: none; }
QTabBar::tab { background: #182330; color: #9caec1; padding: 10px 22px; }
QTabBar::tab:selected { background: #293c50; color: #65d7bd; }
QListWidget, QComboBox { background: #101923; color: #dce5f1; border: 1px solid #35485c; border-radius: 6px; padding: 6px; }
QComboBox QAbstractItemView { background: #182330; color: #dce5f1; selection-background-color: #24655e; }
QListWidget::item:selected { background: #24655e; color: #ffffff; }
QToolTip { color: #101720; background: #e3eef7; }
'''


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('omsipmxtool · PMX 转换器')
        self.resize(940, 810)
        self.setMinimumSize(760, 700)
        self.pool = QThreadPool(self)
        self.work = None
        self.busy = False
        self.last_output = None
        self.accepted_source = None
        self.review_open = False
        self.edited_mapping = None
        self.help_operation = '尚未操作'
        self.help_error = ''
        from .manager import Manager
        self.manager = Manager()
        tabs = QTabWidget(); self.setCentralWidget(tabs)
        root = QWidget(); root.setObjectName('root')
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame); scroll.setWidget(root)
        tabs.addTab(scroll, 'PMX 转换'); tabs.addTab(self.manager, '角色库与游戏')
        page = QVBoxLayout(root); page.setContentsMargins(30, 26, 30, 24); page.setSpacing(16)
        eyebrow = QLabel('omsipmxtool  /  EXPERIMENTAL'); eyebrow.setObjectName('eyebrow'); page.addWidget(eyebrow)
        title = QLabel('让你的角色坐上驾驶座'); title.setObjectName('title'); page.addWidget(title)
        subtitle = QLabel('PMX → OpenOMSI 人物包  ·  自动安装到游戏  ·  一键应用司机'); subtitle.setObjectName('muted'); page.addWidget(subtitle)
        self.form_card = QFrame(); self.form_card.setObjectName('card')
        form = QVBoxLayout(self.form_card); form.setContentsMargins(20,18,20,18); form.setSpacing(12)
        heading = QLabel('01  导入与设置'); heading.setObjectName('section'); form.addWidget(heading)
        self.source = QLineEdit(); self.source.setPlaceholderText('选择人物 .pmx 文件（贴图保留在模型目录中）')
        self.output = QLineEdit(); self.output.setReadOnly(True)
        self.output.setPlaceholderText('选择 OMSI 目录和 PMX 后自动生成')
        self.mapping = QLineEdit(); self.mapping.setPlaceholderText('可选 · 骨骼识别失败时指定 JSON 映射')
        self.game_root = QLineEdit(self.manager.root.text())
        self.game_root.setPlaceholderText('选择包含 maps 和 Vehicles 的 OMSI 安装 / 内容目录')
        self.game_root.textChanged.connect(self.manager.root.setText)
        self.manager.root.textChanged.connect(self.game_root.setText)
        fields = QFormLayout(); fields.setSpacing(10)
        for label, edit, caption, callback in [
            ('人物模型', self.source, '选择 PMX', self.pick_source),
            ('骨骼映射', self.mapping, '选择 JSON', self.pick_mapping),
            ('OMSI 目录', self.game_root, '选择目录', self.manager.pick_root)]:
            row = QHBoxLayout(); row.addWidget(edit,1)
            button = QPushButton(caption); button.clicked.connect(callback); row.addWidget(button)
            if edit is self.mapping:
                self.mapping_button = QPushButton('图形化编辑')
                self.mapping_button.clicked.connect(self.edit_mapping)
                row.addWidget(self.mapping_button)
            fields.addRow(label,row)
        self.mapping_note = QLabel('留空时自动识别，也可点击“图形化编辑”逐项选择。')
        self.mapping_note.setWordWrap(True)
        self.mapping_note.setObjectName('muted')
        fields.addRow('', self.mapping_note)
        self.mapping.textChanged.connect(self.mapping_path_changed)
        fields.addRow('统一导出目录', self.output)
        row = QHBoxLayout()
        self.name = QLineEdit('CustomDriver'); self.name.setToolTip('从 PMX 文件名自动生成拼音标识，可手动修改；中文转拼音，英文和数字保留')
        self.height = QDoubleSpinBox(); self.height.setRange(.5,3); self.height.setValue(1.75); self.height.setSingleStep(.05); self.height.setSuffix(' m'); self.height.setDecimals(2)
        row.addWidget(self.name,1); row.addWidget(QLabel('模型总高度')); row.addWidget(self.height)
        fields.addRow('角色标识',row); form.addLayout(fields)
        self.auto_height = QCheckBox('从 PMX 自动估算高度（可取消后手动调整）')
        self.auto_height.setChecked(True); self.height.setEnabled(False)
        self.auto_height.toggled.connect(lambda enabled: self.height.setEnabled(not enabled))
        self.auto_height.toggled.connect(self.height_mode_changed)
        form.addWidget(self.auto_height)
        self.adapt_thumbs = QCheckBox('适配拇指初始姿态（试验）')
        self.adapt_thumbs.setToolTip('拇指仍有折叠或方向异常时尝试。会调整摊开手掌时的拇指姿态；需同时检查松手和握持效果。')
        form.addWidget(self.adapt_thumbs)
        self.height_note = QLabel('按完整网格高度 × 0.08 换算为米，包含头发和饰品；非标准比例请手动调整。')
        self.height_note.setWordWrap(True); self.height_note.setObjectName('muted'); form.addWidget(self.height_note)
        self.auto_install = QCheckBox('转换后自动安装到 OMSI（包含 HUM、模型和贴图）')
        self.auto_install.setChecked(True)
        form.addWidget(self.auto_install)
        note = QLabel('隐藏层按默认透明度处理，不按厂商或材质名称删除。暂不保留表情和物理。')
        note.setObjectName('muted'); note.setWordWrap(True); form.addWidget(note)
        page.addWidget(self.form_card)
        actions = QHBoxLayout()
        self.inspect_button = QPushButton('检查模型与骨骼'); self.inspect_button.clicked.connect(self.inspect)
        self.convert_button = QPushButton('生成人物包'); self.convert_button.setObjectName('primary'); self.convert_button.clicked.connect(self.convert)
        actions.addWidget(self.inspect_button); actions.addStretch(); actions.addWidget(self.convert_button); page.addLayout(actions)
        self.progress = QProgressBar(); self.progress.setTextVisible(False); self.progress.setRange(0,1); self.progress.setValue(0); page.addWidget(self.progress)
        self.status = QLabel('准备就绪 · 选择一个 PMX 开始'); self.status.setWordWrap(True); page.addWidget(self.status)
        self.summary = QLabel('转换结果将包括 .hum、O3D 网格、PNG 贴图和安装说明。'); self.summary.setObjectName('muted'); self.summary.setWordWrap(True); page.addWidget(self.summary)
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setPlaceholderText('模型信息、骨骼列表和转换报告会显示在这里。'); page.addWidget(self.log,1)
        self.help_button = make_help_button(self); page.addWidget(self.help_button)
        footer = QHBoxLayout()
        self.open_button = QPushButton('打开输出文件夹'); self.open_button.setEnabled(False); self.open_button.clicked.connect(self.open_output)
        foot = QLabel('实验版 0.3 · 文件转换成功不代表游戏内验证通过'); foot.setObjectName('muted')
        footer.addWidget(foot,1); footer.addWidget(self.open_button); page.addLayout(footer)
        self.source.textChanged.connect(self.source_changed)
        self.source.editingFinished.connect(self.inspect_source_if_needed)
        self.name.textChanged.connect(self.update_output)
        self.game_root.textChanged.connect(self.update_output)
        self.inspected_source = None
        self.update_output()
        # Nested form rows can otherwise shrink below their styled size hint,
        # leaving no room for text after padding on a short/high-DPI screen.
        # Let the page scroll instead of squeezing the input controls.
        controls = [control for kind in (QLineEdit, QDoubleSpinBox, QPushButton)
                    for control in self.form_card.findChildren(kind)]
        for control in controls:
            if isinstance(control.parentWidget(), QDoubleSpinBox):
                continue
            control.ensurePolished()
            control.setMinimumHeight(control.sizeHint().height())

    def pick_source(self):
        path,_ = QFileDialog.getOpenFileName(self,'选择 PMX 人物',self.source.text(),'PMX 模型 (*.pmx);;所有文件 (*)')
        if path:
            self.accepted_source = None
            self.source.setText(path)
            self.inspect_source_if_needed()

    def source_changed(self, text):
        self.help_operation, self.help_error = '选择模型', ''
        self.accepted_source = None
        self.inspected_source = None
        self.mapping.clear()
        self.mapping_path_changed()
        self.name.setText(pinyin_name(Path(text).stem))
        self.height_note.setText('等待读取 PMX 高度；按完整网格 × 0.08 换算，包含头发和饰品。')

    def update_output(self, *_):
        try:
            destination = export_destination(self.game_root.text().strip(), self.name.text()) if self.game_root.text().strip() else None
            self.output.setText(str(destination) if destination else '')
        except (ValueError, OSError):
            self.output.clear()

    def inspect_source_if_needed(self):
        if self.source.text().strip() and self.inspected_source != self.source.text() and not self.busy and not self.manager.busy:
            self.inspect()

    def height_mode_changed(self, enabled):
        if enabled:
            self.inspected_source = None
            self.inspect_source_if_needed()

    def pick_mapping(self):
        path,_ = QFileDialog.getOpenFileName(self,'选择骨骼映射','','JSON (*.json)')
        if path:
            self.mapping.setText(path)
            self.mapping_path_changed()

    def mapping_path_changed(self, *_):
        self.edited_mapping = None
        self.mapping_note.setText('使用所选 JSON 文件。' if self.mapping.text().strip() else
                                  '留空时自动识别，也可点击“图形化编辑”逐项选择。')

    def current_mapping(self):
        if self.edited_mapping is not None:
            return dict(self.edited_mapping)
        return Path(self.mapping.text().strip()).expanduser() if self.mapping.text().strip() else None

    def edit_mapping(self):
        if self.busy or self.manager.busy: return
        self.help_operation, self.help_error = '编辑骨骼映射', ''
        try:
            source = self.source_path()
            if not self.review_source(source): return
            mapping = self.current_mapping()
        except (ValueError, OSError) as exc:
            self.failed(str(exc)); return
        def read():
            overrides = mapping if isinstance(mapping, dict) else (
                json.loads(mapping.read_text(encoding='utf-8-sig')) if mapping else {})
            return load(source), overrides
        self.start(read, self.mapping_loaded, '正在读取骨骼映射…')

    def mapping_loaded(self, result):
        from .mapping_editor import MappingEditor
        self.finish()
        try:
            dialog = MappingEditor(result[0], result[1], self)
            if dialog.exec() == dialog.DialogCode.Accepted:
                self.mapping.clear()
                self.edited_mapping = dialog.result_mapping
                self.mapping_note.setText(f'已应用图形化映射：{len(self.edited_mapping)} 个手动指定，其余自动识别。')
                self.status.setText('骨骼映射已更新，可生成人物包。')
            else:
                self.status.setText('已取消骨骼映射编辑，保留原设置。')
            dialog.deleteLater()
        except (ValueError, OSError) as exc:
            self.failed(str(exc))

    def source_path(self):
        if not self.source.text().strip(): raise ValueError('请先选择 PMX 文件。')
        path = Path(self.source.text().strip()).expanduser()
        if not path.is_file(): raise ValueError('PMX 文件不存在，请检查路径。')
        return path

    def review_source(self, source):
        if self.review_open:
            return False
        info = source.stat()
        signature = (str(source.resolve()), info.st_size, info.st_mtime_ns)
        if signature == self.accepted_source:
            return True
        metadata = read_metadata(source)
        if not metadata['comment'].strip() and not metadata['english_comment'].strip():
            self.accepted_source = signature
            return True
        self.review_open = True
        try:
            accepted = ModelNotice(metadata, self).exec() == ModelNotice.DialogCode.Accepted
        finally:
            self.review_open = False
        if not accepted:
            self.status.setText('已取消：尚未确认 PMX 内嵌说明，不会读取模型或转换。')
            return False
        after = source.stat()
        if (after.st_size, after.st_mtime_ns) != (info.st_size, info.st_mtime_ns):
            raise ValueError('PMX 在阅读期间发生变化，请重新选择并阅读说明。')
        self.accepted_source = signature
        return True

    def start(self, function, callback, message):
        if self.busy or self.manager.busy: return
        self.help_operation, self.help_error = message, ''
        self.busy = True
        self.manager.setEnabled(False)
        self.form_card.setEnabled(False); self.inspect_button.setEnabled(False); self.convert_button.setEnabled(False); self.open_button.setEnabled(False)
        self.progress.setRange(0,0); self.status.setText(message)
        self.work = Work(function)
        self.work.events.done.connect(callback)
        self.work.events.failed.connect(self.failed)
        self.pool.start(self.work)

    def finish(self):
        self.busy = False
        self.manager.setEnabled(True)
        self.form_card.setEnabled(True); self.inspect_button.setEnabled(True); self.convert_button.setEnabled(True)
        self.open_button.setEnabled(self.last_output is not None)
        self.progress.setRange(0,1); self.progress.setValue(1)

    def failed(self, message):
        self.help_error = message
        self.finish(); self.progress.setValue(0)
        self.status.setText('操作未完成 · '+message)
        self.log.setPlainText(message)

    def inspect(self):
        if self.busy or self.manager.busy: return
        self.help_operation, self.help_error = '检查模型与骨骼', ''
        try:
            source = self.source_path()
            if not self.review_source(source): return
        except (ValueError, OSError) as exc: self.failed(str(exc)); return
        self.start(lambda: inspect_model(source), self.inspected, '正在读取模型与骨骼…')

    def inspected(self, result):
        self.inspected_source = self.source.text()
        estimate = result['estimated_height']
        if 0.5 <= estimate <= 3:
            if self.auto_height.isChecked(): self.height.setValue(estimate)
            self.height_note.setText(f'PMX 完整网格估算：{estimate:.3f} m（含头发 / 饰品，按 0.08 换算；可手动调整）。')
        else:
            self.height_note.setText(f'估算高度 {estimate:.3f} m 超出 0.5–3 m，请取消自动读取并手动设置。')
        self.finish(); self.status.setText('模型读取完成 · '+result['name'])
        self.summary.setText(f"{result['vertices']:,} 顶点  /  {result['triangles']:,} 三角形  /  {len(result['bones'])} 骨骼  /  {result['materials']} 材质")
        self.log.setPlainText(json.dumps(result,ensure_ascii=False,indent=2))

    def convert(self):
        if self.busy or self.manager.busy:
            self.status.setText('请等待当前转换或游戏应用任务完成。');return
        self.help_operation, self.help_error = '生成人物包', ''
        try:
            source = self.source_path()
            if not self.review_source(source): return
            root = self.manager.content_root()
            name = pinyin_name(self.name.text())
            self.name.setText(name)
            output = export_destination(root, name)
            self.output.setText(str(output))
            height = None if self.auto_height.isChecked() else self.height.value()
            adapt_thumbs = self.adapt_thumbs.isChecked()
            mapping = self.current_mapping()
            game_root = root if self.auto_install.isChecked() else None
            self.manager.library.settings({'root': str(root)})
        except (ValueError, OSError) as exc: self.failed(str(exc)); return
        self.pending_output = output
        self.start(lambda: convert_and_install(source,output,name,height,mapping,self.manager.library,game_root,
                                              adapt_thumbs=adapt_thumbs),
                   self.converted,'正在转换并安装人物包…' if game_root else '正在转换人物包…')

    def converted(self, report):
        self.last_output = self.pending_output.resolve()
        if report.get('height_mode') == 'mmd_bounds_0.08':
            self.height.setValue(report['height'])
            self.height_note.setText(f"本次自动使用模型总高度：{report['height']:.3f} m（完整网格 × 0.08）。")
        self.manager.refresh()
        if report.get('library_id'):self.manager.select_item(report['library_id'])
        self.finish()
        installation=report['installation']
        if installation['status']=='installed':
            self.status.setText('人物包已生成并安装到 OMSI')
            self.summary.setText('已安装：'+installation['hum']+'\n在“角色库与游戏”点击“一键应用全部车辆”即可启用。')
        elif installation['status']=='failed':
            self.help_operation = '人物包已生成，安装或入库失败'
            self.help_error = installation['error']
            self.status.setText('人物包已生成，但安装 / 入库未完成：'+installation['error'])
            self.summary.setText('导出文件已保留；修正目录或权限后，可在角色库中重试应用。')
        else:
            self.status.setText('人物包已生成 · 未自动安装')
            self.summary.setText(f"{report['output_meshes']} 个网格 · 安装方法见输出目录 INSTALL.txt")
        self.log.setPlainText(json.dumps(report,ensure_ascii=False,indent=2))

    def open_output(self):
        if self.last_output: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_output)))

    def closeEvent(self, event):
        if self.busy or self.manager.busy:
            self.status.setText('任务仍在运行，请等待完成后关闭窗口。')
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName('omsipmxtool')
    app.setStyle('Fusion'); app.setStyleSheet(STYLE)
    from .startup_notice import require_startup_notice
    if not require_startup_notice():
        return 0
    window = Window(); window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
