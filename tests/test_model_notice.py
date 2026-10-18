# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from omsimod.pmx import read_metadata, ConversionError
try:
    from PySide6.QtWidgets import QApplication
    from omsimod.model_notice import ModelNotice
    from omsimod.gui import Window, STYLE
    HAS_QT = True
except ImportError:
    HAS_QT = False


def header(comment='', english='', encoding=1):
    data = b'PMX ' + struct.pack('<fB', 2, 8) + bytes([encoding,0,1,1,1,1,1,1])
    for value in ('人物', 'Model', comment, english):
        encoded = value.encode('utf-8' if encoding else 'utf-16-le')
        data += struct.pack('<i',len(encoded)) + encoded
    return data


class MetadataTests(unittest.TestCase):
    def test_both_encodings_preserve_embedded_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'model.pmx'
            for encoding in (0,1):
                path.write_bytes(header('作者说明\r\n禁止配布 <b>原文</b>', 'English notice',encoding))
                info=read_metadata(path)
                self.assertEqual(info['comment'],'作者说明\r\n禁止配布 <b>原文</b>')
                self.assertEqual(info['english_comment'],'English notice')
            path.write_bytes(header('说明')[:-1])
            with self.assertRaises(ConversionError): read_metadata(path)


@unittest.skipUnless(HAS_QT, 'Install GUI extra to run Qt tests')
class NoticeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(STYLE)

    def test_scroll_required_and_accept_cannot_bypass(self):
        notice=ModelNotice(dict(name='人物',english_name='Model',comment='作者说明\n'*300,english_comment='English final line'))
        notice.show(); self.app.processEvents()
        self.assertFalse(notice.proceed.isEnabled())
        notice.accept()
        self.assertTrue(notice.isVisible())
        bar=notice.text.verticalScrollBar();bar.setValue(bar.maximum())
        self.app.processEvents()
        self.assertTrue(notice.proceed.isEnabled())
        self.assertIn('English final line',notice.text.toPlainText())
        notice.proceed.click()
        self.assertEqual(notice.result(),ModelNotice.DialogCode.Accepted)

    def test_short_notice_can_continue_without_artificial_scroll(self):
        notice=ModelNotice(dict(name='人物',english_name='',comment='短说明',english_comment=''))
        notice.show();self.app.processEvents()
        self.assertTrue(notice.proceed.isEnabled());notice.close()

    def test_empty_skips_and_cancel_blocks_inspect_and_convert(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{'OMSIMOD_DATA_DIR':directory}):
            path=Path(directory)/'model.pmx';path.write_bytes(header())
            window=Window();window.source.setText(str(path))
            with patch('omsimod.gui.ModelNotice') as dialog:
                self.assertTrue(window.review_source(path));dialog.assert_not_called()
            path.write_bytes(header('', 'English-only copyright notice'))
            with patch.object(ModelNotice,'exec',return_value=ModelNotice.DialogCode.Rejected) as run:
                with patch.object(window,'start') as start:
                    window.inspect();window.convert()
                    self.assertEqual(run.call_count,2);start.assert_not_called()
            with patch.object(ModelNotice,'exec',return_value=ModelNotice.DialogCode.Accepted) as run:
                self.assertTrue(window.review_source(path))
                self.assertTrue(window.review_source(path))
                self.assertEqual(run.call_count,1)
                window.source_changed(str(path))
                self.assertTrue(window.review_source(path))
                self.assertEqual(run.call_count,2)
            window.close()
