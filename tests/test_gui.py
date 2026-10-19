# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
import os
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtWidgets import QApplication
    from omsimod.gui import Window, STYLE
    HAS_QT = True
except ImportError:
    HAS_QT = False
from test_converter import fixture


@unittest.skipUnless(HAS_QT, 'Install GUI extra to run Qt tests')
class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.library_temp=tempfile.TemporaryDirectory()
        os.environ['OMSIMOD_DATA_DIR']=self.library_temp.name

    def tearDown(self):
        os.environ.pop('OMSIMOD_DATA_DIR',None)
        self.library_temp.cleanup()

    def wait(self, window):
        end = time.monotonic()+20
        while window.busy and time.monotonic()<end:
            self.app.processEvents()
            time.sleep(.01)
        self.assertFalse(window.busy, 'Background job timed out')

    def test_inspect_convert_and_numbered_export(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'模型.pmx'; source.write_bytes(fixture())
            game=Path(temp)/'游戏';(game/'maps').mkdir(parents=True);(game/'Vehicles').mkdir()
            output=game/'omsipmxtool_exports'/'moxing'
            w=Window(); w.source.setText(str(source)); w.game_root.setText(str(game))
            self.assertTrue(w.adapt_thumbs.isChecked())
            w.auto_height.setChecked(False)
            w.auto_install.setChecked(False)
            w.inspect_button.click(); self.assertTrue(w.busy)
            self.wait(w); self.assertIn('模型读取完成',w.status.text())
            w.convert_button.click(); self.wait(w)
            self.assertTrue((output/'conversion-report.json').exists())
            self.assertTrue(w.open_button.isEnabled())
            original=(output/'conversion-report.json').read_bytes()
            w.convert_button.click();self.wait(w)
            self.assertTrue((output.with_name('moxing_2')/'conversion-report.json').is_file())
            self.assertEqual(original,(output/'conversion-report.json').read_bytes())
            w.close()

    def test_ai_help_preview_and_clipboard_are_sanitized(self):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QDialog, QPlainTextEdit, QPushButton
        w = Window()
        w.help_operation = '检查模型'
        w.failed("Missing texture: 'C:/Users/SecretPerson/private/model.png'")
        observed = []
        def copy_and_close():
            dialog = self.app.activeModalWidget()
            if isinstance(dialog, QDialog):
                observed.append(dialog.findChild(QPlainTextEdit).toPlainText())
                for button in dialog.findChildren(QPushButton):
                    if button.text() == '一键复制': button.click()
                dialog.accept()
        QTimer.singleShot(0, copy_and_close)
        w.help_button.click()
        self.assertEqual(len(observed), 1)
        self.assertEqual(self.app.clipboard().text(), observed[0])
        self.assertNotIn('SecretPerson', observed[0])
        self.assertIn('Missing texture', observed[0])
        w.source.setText('another.pmx')
        self.assertEqual(w.help_error, '')
        w.manager.record_error('Permission denied: D:/SecretPerson/game')
        self.assertIn('Permission denied', w.manager.help_error)
        w.manager.success_message = '完成'
        w.manager.job_done('成功 1\n失败：地图A：文件占用')
        self.assertIn('文件占用', w.manager.help_error)
        w.manager.job_done('成功 2')
        self.assertEqual(w.manager.help_error, '')
        w.close()

    def test_auto_install_and_apply_all_then_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);game=base/'游戏';(game/'Vehicles').mkdir(parents=True)
            originals={}
            for name in ('MapA','地图B'):
                folder=game/'maps'/name;folder.mkdir(parents=True)
                (folder/'global.cfg').write_text('map')
                originals[name]=b'old\\driver.hum\r\n'
                (folder/'drivers.txt').write_bytes(originals[name])
            source=base/'人物.pmx';source.write_bytes(fixture())
            output=base/'export'
            w=Window();w.source.setText(str(source));w.output.setText(str(output))
            w.auto_height.setChecked(False)
            w.game_root.setText(str(game));w.convert_button.click();self.wait(w)
            self.assertIn('已生成并安装',w.status.text())
            item=w.manager.current()
            installed=game/'Humans'/('OMSIMod_'+item['id'])/'driver.hum'
            self.assertTrue(installed.is_file())
            self.assertTrue(list(installed.parent.rglob('*.o3d')))
            self.assertTrue(list(installed.parent.rglob('*.png')))
            for name,data in originals.items():
                self.assertEqual((game/'maps'/name/'drivers.txt').read_bytes(),data)
            w.manager.all_maps.setChecked(False)  # Dedicated button must ignore this scope.
            w.manager.apply_all_button.click()
            end=time.monotonic()+20
            while w.manager.busy and time.monotonic()<end:
                self.app.processEvents();time.sleep(.01)
            self.assertFalse(w.manager.busy)
            self.assertIn('成功 2',w.manager.details.toPlainText())
            for name in originals:
                self.assertIn(b'OMSIMod_', (game/'maps'/name/'drivers.txt').read_bytes())
            w.manager.library.batch(game)
            for name,data in originals.items():
                self.assertEqual((game/'maps'/name/'drivers.txt').read_bytes(),data)
            w.close()

    def test_install_failure_preserves_export(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);game=base/'game'
            (game/'maps').mkdir(parents=True);(game/'Vehicles').mkdir()
            source=base/'model.pmx';source.write_bytes(fixture())
            w=Window();w.source.setText(str(source));w.output.setText(str(base/'export'))
            w.auto_height.setChecked(False)
            w.game_root.setText(str(game))
            with patch.object(w.manager.library,'install',side_effect=PermissionError('permission denied')):
                w.convert_button.click();self.wait(w)
            self.assertIn('未完成',w.status.text())
            self.assertTrue((game/'omsipmxtool_exports/model/Humans/model/driver.hum').is_file())
            self.assertTrue(w.open_button.isEnabled())
            self.assertEqual(len(w.manager.library.data['characters']),1)
            w.close()

    def test_auto_install_requires_valid_game_before_export(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);source=base/'model.pmx';source.write_bytes(fixture())
            w=Window();w.source.setText(str(source));w.output.setText(str(base/'export'))
            w.game_root.setText(str(base/'wrong-directory'))
            w.convert_button.click()
            self.assertFalse(w.busy)
            self.assertFalse((base/'export').exists())
            self.assertIn('maps 和 Vehicles',w.status.text())
            w.close()

    def test_missing_source(self):
        w=Window(); w.inspect_button.click()
        self.assertIn('请先选择', w.status.text())
        self.assertFalse(w.busy); w.close()

    def test_mapping_editor_validation_save_and_load(self):
        import json
        from omsimod.mapping_editor import MappingEditor
        from omsimod.pmx import load
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'model.pmx'; source.write_bytes(fixture())
            model = load(source)
            model.bones[1].name = 'custom torso'
            dialog = MappingEditor(model)
            dialog.apply()
            self.assertIn('请修正', dialog.message.text())
            combo = dialog.combos['torso']
            combo.setCurrentIndex(combo.findData('custom torso'))
            self.assertEqual(dialog.mapping(), {'torso': 'custom torso'})
            path = Path(temp)/'mapping.json'
            with patch('omsimod.mapping_editor.QFileDialog.getSaveFileName', return_value=(str(path), '')):
                dialog.save_file()
            self.assertEqual(json.loads(path.read_text()), {'torso': 'custom torso'})
            dialog.set_mapping({})
            with patch('omsimod.mapping_editor.QFileDialog.getOpenFileName', return_value=(str(path), '')):
                dialog.load_file()
            self.assertEqual(dialog.mapping(), {'torso': 'custom torso'})
            dialog.set_mapping({'torso': 'missing bone'})
            dialog.apply(); self.assertIn('请修正', dialog.message.text())
            dialog.set_mapping({'torso': 'head'})
            dialog.apply(); self.assertIn('different bone', dialog.message.text())
            dialog.set_mapping({'torso': 'custom torso'})
            combo.setEditText('unfinished search')
            dialog.apply(); self.assertIn('下拉列表', dialog.message.text())
            dialog.set_mapping({'torso': 'custom torso'})
            dialog.apply()
            self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)
            dialog.close()

    def test_bone_combo_wheel_does_not_change_mapping(self):
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        from omsimod.mapping_editor import BoneComboBox
        combo = BoneComboBox(); combo.setEditable(True)
        combo.addItems(['自动识别', '左足', '左足D'])
        combo.setCurrentIndex(1)
        combo.show(); combo.setFocus(); self.app.processEvents()
        for delta in (-120, 120):
            event = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(), QPoint(0, delta),
                                Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                                Qt.ScrollPhase.NoScrollPhase, False)
            QApplication.sendEvent(combo, event)
            self.assertEqual(combo.currentIndex(), 1)
            self.assertFalse(event.isAccepted())
        combo.close()

    def test_preview_click_highlight_and_mapping_export(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from omsimod.mapping_editor import MappingEditor
        from omsimod.pmx import load, Bone
        from omsimod.export import convert
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'model.pmx'; source.write_bytes(fixture())
            model = load(source)
            model.bones.append(Bone('左足D', '', model.bones[4].position, 0))
            dialog = MappingEditor(model); dialog.show(); self.app.processEvents()
            dialog.show_role('left_thigh')
            self.assertEqual(dialog.preview.selected, 4)
            point = dialog.preview.projected(dialog.preview.bones)[4][0]
            QTest.mouseClick(dialog.preview, Qt.MouseButton.LeftButton, pos=point.toPoint())
            self.assertEqual(dialog.candidates.count(), 2)
            dialog.candidates.setCurrentIndex(dialog.candidates.findData(15))
            self.assertEqual(dialog.preview.selected, 15)
            # Picking only previews; mapping changes after the explicit button.
            self.assertEqual(dialog.mapping(), {})
            dialog.assign_button.click()
            self.assertEqual(dialog.mapping()['left_thigh'], '左足D')
            report = convert(model, source, Path(temp)/'export', 'Preview', 1.75, dialog.mapping())
            self.assertEqual(report['joints']['left_thigh'], '左足D')
            self.assertIsNotNone(dialog.preview.mesh_cache)
            dialog.set_mapping({}); self.assertEqual(dialog.preview.selected, 4)
            dialog.close()

    def test_preview_camera_and_empty_selection_do_not_change_mapping(self):
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtTest import QTest
        from omsimod.mapping_editor import MappingEditor
        from omsimod.pmx import load
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'model.pmx'; source.write_bytes(fixture())
            dialog = MappingEditor(load(source)); dialog.show(); self.app.processEvents()
            preview = dialog.preview
            before = preview.projected(preview.bones)[4][0]
            QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=QPoint(100, 100))
            QTest.mouseMove(preview, QPoint(160, 120))
            QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=QPoint(160, 120))
            self.assertNotEqual(preview.yaw, 0)
            self.assertNotEqual(before, preview.projected(preview.bones)[4][0])
            event = QWheelEvent(QPointF(100, 100), QPointF(100, 100), QPoint(), QPoint(0, 120),
                                Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                                Qt.ScrollPhase.NoScrollPhase, False)
            QApplication.sendEvent(preview, event)
            self.assertGreater(preview.zoom, 1)
            self.assertEqual(dialog.mapping(), {})
            preview.reset_view(); self.assertEqual(preview.zoom, 1)
            self.assertEqual(preview.yaw, 0)
            QTest.mouseClick(preview, Qt.MouseButton.LeftButton, pos=QPoint(2, 2))
            self.assertFalse(dialog.assign_button.isEnabled())
            self.assertIsNone(preview.selected)
            dialog.close()

    def test_large_preview_falls_back_without_allocating_mesh(self):
        from omsimod.pmx import load
        from omsimod.model_preview import ModelPreview
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'model.pmx'; source.write_bytes(fixture())
            model = load(source)
            model.indices = model.indices * (ModelPreview.MAX_FACES + 1)
            view = ModelPreview(model)
            self.assertTrue(view.mesh_limited)
            self.assertEqual(view.vertices, [])
            self.assertEqual(view.faces, [])
            self.assertEqual(len(view.bones), len(model.bones))
            self.assertEqual(len(model.indices), 3*(ModelPreview.MAX_FACES+1))
            view.close()

    def test_preview_render_yields_and_camera_invalidates_pending_frame(self):
        from PySide6.QtCore import QTimer
        from omsimod.pmx import load
        from omsimod.model_preview import ModelPreview
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'model.pmx'; source.write_bytes(fixture())
            model = load(source)
            model.indices *= 20000; model.materials[0].count = len(model.indices)
            view = ModelPreview(model); view.resize(500,500)
            view.render_mesh()
            self.assertIsNotNone(view.render_steps)
            serviced = []
            QTimer.singleShot(0, lambda: serviced.append(True))
            self.app.processEvents()
            self.assertTrue(serviced)
            view.yaw = .5; view.invalidate()
            self.assertIsNone(view.render_steps)
            self.assertFalse(view.render_timer.isActive())
            view.render_mesh()
            end = time.monotonic()+10
            while view.render_steps is not None and time.monotonic() < end:
                self.app.processEvents(); time.sleep(.002)
            self.assertIsNone(view.render_steps)
            self.assertFalse(view.mesh_cache.isNull())
            view.close()

    def test_mapping_editor_applies_to_conversion_and_resets_on_source_change(self):
        import json
        from omsimod.mapping_editor import MappingEditor
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); source = base/'model.pmx'
            source.write_bytes(fixture())
            game = base/'game'; (game/'maps').mkdir(parents=True); (game/'Vehicles').mkdir()
            w = Window(); w.source.setText(str(source)); w.game_root.setText(str(game))
            w.auto_height.setChecked(False); w.auto_install.setChecked(False)
            def choose(dialog):
                dialog.set_mapping({'torso': 'chest'})
                dialog.apply()
                return dialog.result()
            with patch.object(MappingEditor, 'exec', choose):
                w.mapping_button.click(); self.wait(w)
            self.assertEqual(w.current_mapping(), {'torso': 'chest'})
            w.convert_button.click(); self.wait(w)
            report = json.loads((w.last_output/'conversion-report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['joints']['torso'], 'chest')
            with patch.object(MappingEditor, 'exec', return_value=MappingEditor.DialogCode.Rejected):
                w.mapping_button.click(); self.wait(w)
            self.assertEqual(w.current_mapping(), {'torso': 'chest'})
            w.source.setText(str(base/'other.pmx'))
            self.assertIsNone(w.current_mapping())
            w.close()

    def test_selection_survives_catalogue_reload_from_other_window(self):
        from omsimod.library import Library
        w=Window();lib=w.manager.library
        first={'id':'first','name':'First','hum':'first/driver.hum'}
        second={'id':'second','name':'Second','hum':'second/driver.hum'}
        lib.data['characters']=[first,second];lib.save()
        w.manager.refresh();w.manager.list.setCurrentRow(0)
        other=Library(lib.directory);other.remove('first')
        lib.settings({'test':True})  # Reloads the catalogue without redrawing the list.
        self.assertEqual(w.manager.current()['id'],'first')
        w.manager.remove()  # Must never remove Second, shown on a different row.
        self.assertEqual([x['id'] for x in lib.data['characters']],['second'])
        w.close()

    def test_filename_and_automatic_height(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);game=base/'game'
            (game/'maps').mkdir(parents=True);(game/'Vehicles').mkdir()
            source=base/'饮月君 1708.pmx';source.write_bytes(fixture(scale=12.5))
            w=Window();w.game_root.setText(str(game))
            with patch('omsimod.gui.QFileDialog.getOpenFileName',return_value=(str(source),'')):
                w.pick_source();self.wait(w)
            self.assertEqual(w.name.text(),'yinyuejun_1708')
            self.assertAlmostEqual(w.height.value(),2)
            self.assertTrue(w.output.isReadOnly())
            w.convert_button.click();self.wait(w)
            self.assertIn('已生成并安装',w.status.text())
            import json
            report=json.loads((w.last_output/'conversion-report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['height'],2)
            self.assertEqual(report['height_mode'],'mmd_bounds_0.08')
            self.assertEqual(report['character'],'yinyuejun_1708')
            w.close()

    def test_unusual_scale_requires_manual_height(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);(base/'maps').mkdir();(base/'Vehicles').mkdir()
            source=base/'model.pmx';source.write_bytes(fixture())
            w=Window();w.source.setText(str(source));w.game_root.setText(str(base))
            w.convert_button.click();self.wait(w)
            self.assertIn('手动设置',w.status.text())
            self.assertFalse((base/'omsipmxtool_exports').exists())
            w.auto_height.setChecked(False);w.height.setValue(1.8)
            w.convert_button.click();self.wait(w)
            self.assertIn('已生成并安装',w.status.text());w.close()
