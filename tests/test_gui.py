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

    def test_inspect_convert_and_overwrite_error(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'模型.pmx'; source.write_bytes(fixture())
            output=Path(temp)/'结果'
            w=Window(); w.source.setText(str(source)); w.output.setText(str(output))
            w.auto_install.setChecked(False)
            w.inspect_button.click(); self.assertTrue(w.busy)
            self.wait(w); self.assertIn('模型读取完成',w.status.text())
            w.convert_button.click(); self.wait(w)
            self.assertTrue((output/'conversion-report.json').exists())
            self.assertTrue(w.open_button.isEnabled())
            w.convert_button.click()
            self.assertIn('已存在',w.status.text())
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
            w.game_root.setText(str(game))
            with patch.object(w.manager.library,'install',side_effect=PermissionError('permission denied')):
                w.convert_button.click();self.wait(w)
            self.assertIn('未完成',w.status.text())
            self.assertTrue((base/'export/Humans/CustomDriver/driver.hum').is_file())
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
