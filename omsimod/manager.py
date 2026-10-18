# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Character catalogue, map selection and reversible game activation UI."""
import subprocess
import os
from pathlib import Path
from PySide6.QtCore import QThreadPool, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,
    QLineEdit,QPushButton,QFileDialog,QComboBox,QListWidget,QListWidgetItem,QPlainTextEdit,QCheckBox)
from .library import Library,game_command
from .paths import prepare_data_directory


class Manager(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("manager"); self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True)
        self.library=Library(prepare_data_directory())
        self.pool=QThreadPool(self);self.busy=False;self.child=None
        layout=QVBoxLayout(self);layout.setContentsMargins(24,24,24,24);layout.setSpacing(12)
        title=QLabel('角色库与游戏');title.setObjectName('title');layout.addWidget(title)
        note=QLabel('一键应用覆盖全部已安装地图中的动态司机，切换车辆无需重新设置。车辆需支持司机显示；不替换车辆自带的固定人物。AI 也可能使用所选角色。')
        note.setWordWrap(True);layout.addWidget(note)
        self.controls=QWidget();body=QVBoxLayout(self.controls);body.setContentsMargins(0,0,0,0)
        self.list=QListWidget();body.addWidget(self.list)
        row=QHBoxLayout()
        for name,call in [('导入 HUM',self.import_hum),('移出角色库',self.remove),('打开人物目录',self.reveal)]:
            b=QPushButton(name);b.clicked.connect(call);row.addWidget(b)
        body.addLayout(row)
        self.executable=QLineEdit(self.library.data['settings'].get('executable',''))
        self.root=QLineEdit(self.library.data['settings'].get('root',''))
        form=QFormLayout()
        for label,edit,call in [('游戏程序',self.executable,self.pick_exe),('OMSI 内容目录',self.root,self.pick_root)]:
            row=QHBoxLayout();row.addWidget(edit);b=QPushButton('选择');b.clicked.connect(call);row.addWidget(b);form.addRow(label,row)
        self.maps=QComboBox();self.buses=QComboBox()
        form.addRow('地图',self.maps);form.addRow('车辆',self.buses);body.addLayout(form)
        refresh=QPushButton('保存路径并扫描地图 / 车辆');refresh.clicked.connect(self.scan);body.addWidget(refresh)
        self.all_maps=QCheckBox('应用 / 恢复全部已安装地图（以后新增地图需再次应用）')
        self.all_maps.setChecked(True);body.addWidget(self.all_maps)
        self.apply_all_button=QPushButton('一键应用全部车辆（全部地图）')
        self.apply_all_button.setObjectName('primary')
        self.apply_all_button.clicked.connect(self.apply_all)
        body.addWidget(self.apply_all_button)
        row=QHBoxLayout()
        for name,call in [('应用所选角色',self.apply),('恢复原司机',self.restore),('启动所选地图 / 车辆（可选）',self.launch)]:
            b=QPushButton(name);b.clicked.connect(call);row.addWidget(b)
        body.addLayout(row);layout.addWidget(self.controls)
        self.status=QLabel('导入完整人物目录中的 .hum，或转换后加入角色库。');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.details=QPlainTextEdit();self.details.setReadOnly(True);layout.addWidget(self.details)
        self.list.currentRowChanged.connect(self.selected)
        self.refresh();self.scan(silent=True)

    def refresh(self):
        self.list.clear()
        for item in self.library.data['characters']:
            row=QListWidgetItem(item['name']+'  ·  '+Path(item['hum']).name)
            row.setData(Qt.ItemDataRole.UserRole, dict(item))
            self.list.addItem(row)
        if self.list.count():self.list.setCurrentRow(0)

    def current(self):
        row=self.list.currentItem()
        if row is None:raise ValueError('请先选择角色')
        return dict(row.data(Qt.ItemDataRole.UserRole))

    def selected(self,*_):
        if self.list.currentRow()>=0:
            item=self.current();self.details.setPlainText(item['hum']+'\n\n角色库记录文件位置，不复制或删除源人物。\n当前仅支持资源位于人物目录内的独立包。')

    def add_path(self,path):
        item=self.library.add(path);self.refresh();self.select_item(item['id']);self.status.setText('已加入角色库')

    def select_item(self,key):
        for index,item in enumerate(self.library.data['characters']):
            if item['id']==key:
                self.list.setCurrentRow(index);break

    def content_root(self):
        if not self.root.text().strip():raise ValueError('请先选择 OMSI 内容目录')
        root=Path(self.root.text().strip()).expanduser().resolve()
        if not (root/'maps').is_dir() or not (root/'Vehicles').is_dir():
            raise ValueError('OMSI 内容目录必须包含 maps 和 Vehicles')
        return root

    def import_hum(self):
        path,_=QFileDialog.getOpenFileName(self,'导入已有 HUM 人物','','人物文件 (*.hum)')
        if path:
            try:self.add_path(path)
            except Exception as e:self.status.setText(str(e))

    def remove(self):
        try:self.library.remove(self.current()['id']);self.refresh();self.status.setText('已移出列表；源文件和已安装人物未删除。')
        except Exception as e:self.status.setText(str(e))

    def reveal(self):
        try:QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.current()['hum']).parent)))
        except Exception as e:self.status.setText(str(e))

    def pick_exe(self):
        path,_=QFileDialog.getOpenFileName(self,'选择 openomsi / openomsi.exe')
        if path:self.executable.setText(path)

    def pick_root(self):
        path=QFileDialog.getExistingDirectory(self,'选择包含 maps 和 Vehicles 的目录')
        if path:self.root.setText(path);self.scan()

    def scan(self,*_,silent=False):
        try:
            self.maps.clear();self.buses.clear()
            root=Path(self.root.text()).expanduser()
            if not (root/'maps').is_dir() or not (root/'Vehicles').is_dir():
                raise ValueError('内容目录必须包含 maps 和 Vehicles')
            for p in sorted((root/'maps').glob('*/global.cfg')):self.maps.addItem(p.parent.name)
            for p in sorted((root/'Vehicles').rglob('*.bus')):self.buses.addItem(p.relative_to(root).as_posix())
            for combo,value in [(self.maps,'Grundorf'),(self.buses,'Vehicles/MAN_SD200/MAN_SD80.bus')]:
                index=combo.findText(value)
                if index>=0:combo.setCurrentIndex(index)
            self.library.settings({'root':str(root),'executable':self.executable.text().strip()})
            self.status.setText(f'找到 {self.maps.count()} 张地图和 {self.buses.count()} 辆车。')
        except Exception as e:
            if not silent:self.status.setText(str(e))

    def run(self,fn,success):
        from .gui import Work
        if self.busy:return
        self.busy=True;self.controls.setEnabled(False);self.status.setText('正在处理…')
        self.worker=Work(fn)
        self.success_message=success
        self.worker.events.done.connect(self.job_done);self.worker.events.failed.connect(self.job_failed);self.pool.start(self.worker)

    def job_done(self,value):
        self.busy=False;self.controls.setEnabled(True);self.status.setText(self.success_message)
        self.details.setPlainText(str(value or self.success_message))

    def job_failed(self,message):
        self.busy=False;self.controls.setEnabled(True);self.status.setText('未完成：'+message)

    def apply(self):
        try:
            item=self.current();root=self.root.text().strip();map_name=self.maps.currentText()
            if self.all_maps.isChecked():
                if not root:raise ValueError('请先选择内容目录')
                self.run(lambda:self.library.batch(root,item),'批量应用已结束，请查看下方结果。成功的地图重启游戏后生效，无需从本工具启动。')
                return
            if not root or not map_name:raise ValueError('请先扫描内容目录并选择地图')
            self.run(lambda:self.library.activate(item,root,map_name),'角色已应用。重启游戏后生效，无需从本工具启动。')
        except Exception as e:self.status.setText(str(e))

    def apply_all(self):
        try:
            item=self.current();root=self.content_root()
            self.library.settings({'root':str(root),'executable':self.executable.text().strip()})
            self.run(lambda:self.library.batch(root,item),
                     '一键应用已结束，请查看成功与失败列表。重启游戏后，成功地图内支持动态司机的车辆均可使用。')
        except Exception as e:self.status.setText(str(e))

    def restore(self):
        root=self.root.text().strip();map_name=self.maps.currentText()
        if not root:self.status.setText('请先选择内容目录');return
        if self.all_maps.isChecked():
            self.run(lambda:self.library.batch(root),'批量恢复已结束，请查看下方结果。未备份的地图不变。')
            return
        self.run(lambda:self.library.restore(root,map_name),'已恢复原司机列表；人物资源保留以免影响其他地图。')

    def launch(self):
        try:
            if self.child and self.child.poll() is None:raise ValueError('本工具启动的游戏仍在运行，请先退出。')
            cmd=game_command(self.executable.text().strip(),self.root.text().strip(),self.maps.currentText(),self.buses.currentText())
            log=self.library.directory/'game-launch.log'
            with log.open('ab') as stream:
                self.child=subprocess.Popen(cmd,stdout=stream,stderr=stream,cwd=self.library.directory)
            self.status.setText('游戏已启动。若退出，请查看下方日志文件。');self.details.setPlainText(str(log))
        except Exception as e:self.status.setText(str(e))
