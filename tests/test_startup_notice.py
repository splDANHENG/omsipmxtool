# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from omsimod.model_notice import ModelNotice
    from omsimod.startup_notice import require_startup_notice
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, 'Install GUI extra to run Qt tests')
class StartupNoticeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_first_read_saved_repeat_skipped_and_change_reprompts(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, OMSIMOD_DATA_DIR=directory):
            checks = []
            def read():
                dialog = next(w for w in self.app.topLevelWidgets()
                              if isinstance(w, ModelNotice) and w.isVisible())
                checks.append(not dialog.proceed.isEnabled())
                dialog.accept()
                checks.append(dialog.isVisible())
                bar = dialog.text.verticalScrollBar()
                bar.setValue(bar.maximum())
                dialog.check_end()
                dialog.proceed.click()
            QTimer.singleShot(100, read)
            self.assertTrue(require_startup_notice())
            self.assertEqual(checks, [True, True])
            record = Path(directory)/'model-rights-read.txt'
            self.assertTrue(record.is_file())
            with patch.object(ModelNotice, 'exec', side_effect=AssertionError('should skip')):
                self.assertTrue(require_startup_notice())
            record.write_text('old version', encoding='ascii')
            with patch.object(ModelNotice, 'exec', return_value=ModelNotice.DialogCode.Rejected) as show:
                self.assertFalse(require_startup_notice())
                show.assert_called_once()
            self.assertEqual(record.read_text(), 'old version')

    def test_cancel_does_not_save_and_documents_match(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, OMSIMOD_DATA_DIR=directory):
            with patch.object(ModelNotice, 'exec', return_value=ModelNotice.DialogCode.Rejected):
                self.assertFalse(require_startup_notice())
            self.assertFalse((Path(directory)/'model-rights-read.txt').exists())
        root = Path(__file__).resolve().parents[1]
        self.assertEqual((root/'MODEL-RIGHTS.txt').read_bytes(),
                         (root/'omsimod'/'MODEL-RIGHTS.txt').read_bytes())

    def test_legacy_backup_migrates_before_notice_record(self):
        from omsimod.paths import migrate_legacy
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'legacy';source.mkdir()
            (source/'map.activation.json').write_text('backup')
            target=Path(directory)/'new'
            def prepare():
                migrate_legacy(source,target)
                return target
            def read():
                dialog=next(w for w in self.app.topLevelWidgets()
                            if isinstance(w,ModelNotice) and w.isVisible())
                bar=dialog.text.verticalScrollBar();bar.setValue(bar.maximum())
                dialog.check_end();dialog.proceed.click()
            with patch('omsimod.startup_notice.prepare_data_directory',side_effect=prepare):
                QTimer.singleShot(100,read)
                self.assertTrue(require_startup_notice())
            self.assertEqual((target/'map.activation.json').read_text(),'backup')
            self.assertTrue((target/'model-rights-read.txt').exists())
